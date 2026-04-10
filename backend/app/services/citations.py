"""Citation formatter — supports APA, MLA, and Chicago styles."""


def _author_list(authors: list[str]) -> str:
    return ", ".join(authors) if authors else "Unknown Author"


def _first_author_last(authors: list[str]) -> str:
    """Return 'LastName, F.' style for the first author."""
    if not authors:
        return "Unknown Author"
    parts = authors[0].split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {parts[0][0]}."
    return authors[0]


def format_apa(metadata: dict) -> str:
    """Return an APA-style citation string."""
    authors = metadata.get("authors", [])
    year = metadata.get("year", "n.d.")
    title = metadata.get("title", "Untitled")
    journal = metadata.get("journal", metadata.get("source", ""))
    url = metadata.get("url", "")

    author_str = _author_list(authors)
    parts = [f"{author_str} ({year}). {title}."]
    if journal:
        parts.append(f" {journal}.")
    if url:
        parts.append(f" {url}")
    return "".join(parts)


def format_mla(metadata: dict) -> str:
    """Return an MLA-style citation string."""
    authors = metadata.get("authors", [])
    year = metadata.get("year", "n.d.")
    title = metadata.get("title", "Untitled")
    journal = metadata.get("journal", metadata.get("source", ""))
    url = metadata.get("url", "")

    author_str = _first_author_last(authors)
    parts = [f'{author_str}. "{title}."']
    if journal:
        parts.append(f" {journal},")
    parts.append(f" {year}.")
    if url:
        parts.append(f" {url}.")
    return "".join(parts)


def format_chicago(metadata: dict) -> str:
    """Return a Chicago-style citation string."""
    authors = metadata.get("authors", [])
    year = metadata.get("year", "n.d.")
    title = metadata.get("title", "Untitled")
    journal = metadata.get("journal", metadata.get("source", ""))
    url = metadata.get("url", "")

    author_str = _author_list(authors)
    parts = [f"{author_str}. \"{title}.\""]
    if journal:
        parts.append(f" {journal}")
    parts.append(f" ({year}).")
    if url:
        parts.append(f" {url}.")
    return "".join(parts)
