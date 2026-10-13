import hashlib
import os
import tempfile
from pathlib import Path

import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


st.set_page_config(page_title="Multi-PDF RAG App", page_icon="📚", layout="wide")
st.title("📚 Multi-PDF RAG App")
st.write("Upload multiple PDFs, ask questions across them, and inspect the source pages.")

# The assignment requires the API key to be read from an environment variable.
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error(
        "OPENAI_API_KEY is not set. Set it in your terminal, then restart Streamlit."
    )
    st.code('$env:OPENAI_API_KEY="your-api-key"  # Windows PowerShell')
    st.stop()

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

# Initialise session state.
if "store" not in st.session_state:
    st.session_state.store = None
if "indexed_signature" not in st.session_state:
    st.session_state.indexed_signature = None
if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []
if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

def upload_signature(files):
    """Return a stable signature so the same upload is not indexed repeatedly."""
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.name.encode("utf-8"))
        digest.update(file.getvalue())
    return digest.hexdigest()

if uploaded_files:
    signature = upload_signature(uploaded_files)
    if signature != st.session_state.indexed_signature:
        if st.button("Build / rebuild document index", type="primary"):
            all_chunks = []
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                add_start_index=True,
            )

            progress = st.progress(0, text="Preparing PDFs...")
            total_files = len(uploaded_files)

            with tempfile.TemporaryDirectory() as temp_dir:
                for index, uploaded_file in enumerate(uploaded_files, start=1):
                    safe_name = Path(uploaded_file.name).name
                    pdf_path = Path(temp_dir) / f"{index}_{safe_name}"
                    pdf_path.write_bytes(uploaded_file.getvalue())

                    try:
                        pages = PyPDFLoader(str(pdf_path)).load()
                    except Exception as exc:
                        st.warning(f"Could not read {uploaded_file.name}: {exc}")
                        continue

                    # Keep a clean original filename and human-readable page number
                    # in metadata. PyPDFLoader's page metadata is zero-indexed.
                    for page in pages:
                        page.metadata["source"] = uploaded_file.name
                        page.metadata["page"] = int(page.metadata.get("page", 0)) + 1

                    all_chunks.extend(splitter.split_documents(pages))
                    progress.progress(
                        index / total_files,
                        text=f"Processed {index} of {total_files} PDF(s)...",
                    )

            if not all_chunks:
                st.error("No readable text was found in the uploaded PDFs.")
            else:
                with st.spinner("Creating embeddings and building the FAISS index..."):
                    embeddings = OpenAIEmbeddings(api_key=api_key)
                    st.session_state.store = FAISS.from_documents(
                        all_chunks, embeddings
                    )
                    st.session_state.indexed_signature = signature
                    st.session_state.indexed_files = [f.name for f in uploaded_files]
                    st.session_state.chunk_count = len(all_chunks)
                st.success(
                    f"Indexed {len(all_chunks)} chunks from "
                    f"{len(st.session_state.indexed_files)} PDF(s)."
                )
    else:
        st.success(
            f"Index ready: {st.session_state.chunk_count} chunks from "
            f"{len(st.session_state.indexed_files)} PDF(s)."
        )
else:
    st.info("Upload PDFs above to get started.")

if st.session_state.store is not None:
    with st.sidebar:
        st.subheader("Indexed documents")
        for filename in st.session_state.indexed_files:
            st.write(f"📄 {filename}")
        st.metric("Chunks indexed", st.session_state.chunk_count)
        st.caption("Page numbers shown in citations are 1-based PDF page numbers.")

    st.divider()
    st.subheader("Ask a question")
    question = st.text_input(
        "Your question",
        placeholder="Example: How many leave days do new joiners get?",
    )
    k = st.slider("Number of source chunks to retrieve", min_value=2, max_value=10, value=5)

    if st.button("Get answer", type="primary", disabled=not question.strip()):
        with st.spinner("Searching all indexed PDFs and preparing an answer..."):
            retriever = st.session_state.store.as_retriever(
                search_kwargs={"k": k}
            )
            docs = retriever.invoke(question)

            if not docs:
                st.warning("No relevant passages were found in the indexed PDFs.")
            else:
                context_parts = []
                for i, doc in enumerate(docs, start=1):
                    source = doc.metadata.get("source", "Unknown file")
                    page = doc.metadata.get("page", "Unknown page")
                    context_parts.append(
                        f"[Source {i}: {source}, page {page}]\n{doc.page_content}"
                    )
                context = "\n\n".join(context_parts)

                system_prompt = """You answer questions using only the supplied PDF excerpts.
If the excerpts do not contain enough information, say that the documents do not
provide enough information. Do not invent facts or citations. If sources disagree,
explicitly describe the disagreement and cite each conflicting source. Distinguish
a direct statement in the documents from an inference. Cite claims inline using
the source labels exactly as supplied, for example [Source 1: handbook.pdf, page 7]."""
                model = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0,
                    api_key=api_key,
                )
                response = model.invoke(
                    [
                        ("system", system_prompt),
                        (
                            "human",
                            f"Question: {question}\n\nPDF excerpts:\n{context}",
                        ),
                    ]
                )

                st.markdown("### Answer")
                st.markdown(response.content)

                st.markdown("### Retrieved sources")
                seen = set()
                for doc in docs:
                    source = doc.metadata.get("source", "Unknown file")
                    page = doc.metadata.get("page", "Unknown page")
                    key = (source, page)
                    if key not in seen:
                        seen.add(key)
                        st.caption(f"📄 {source} — page {page}")
                        with st.expander(f"View excerpt: {source}, page {page}"):
                            st.write(doc.page_content)
