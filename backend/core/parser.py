"""文档解析 —— 支持 .md / .txt / .docx / .pdf"""
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core import config as cfg


def parse_markdown(filepath: str) -> str:
    return Path(filepath).read_text(encoding="utf-8")


def parse_text(filepath: str) -> str:
    return Path(filepath).read_text(encoding="utf-8")


def parse_docx(filepath: str) -> str:
    from docx import Document as DocxDoc
    doc = DocxDoc(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_pdf(filepath: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(filepath)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


PARSERS = {
    ".md": parse_markdown,
    ".txt": parse_text,
    ".docx": parse_docx,
    ".pdf": parse_pdf,
}


def parse_file(filepath: str) -> str:
    """根据扩展名选解析器"""
    ext = Path(filepath).suffix.lower()
    if ext not in PARSERS:
        raise ValueError(f"不支持的文件类型: {ext}，支持: {list(PARSERS.keys())}")
    return PARSERS[ext](filepath)


def split_text(text: str, source: str, device: str = None, security_level: str = "V1") -> list[Document]:
    """分块 —— 500 字符 + 50 重叠，带 metadata（source/device/security_level）"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.CHUNK_SIZE,
        chunk_overlap=cfg.CHUNK_OVERLAP,
        length_function=len,
    )
    chunks = splitter.create_documents([text])
    for c in chunks:
        c.metadata["source"] = source
        if device:
            c.metadata["device"] = device
        c.metadata["security_level"] = security_level
    return chunks
