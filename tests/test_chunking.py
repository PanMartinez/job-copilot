from app.rag.chunking import chunk_text


def test_empty_content_returns_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_returns_single_chunk() -> None:
    chunks = chunk_text("I am a backend engineer with five years of experience building APIs.")
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert "backend engineer" in chunks[0].content


def test_chunk_indices_are_sequential() -> None:
    long_text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(long_text)
    assert len(chunks) > 1
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunks_never_empty() -> None:
    long_text = "\n\n".join(f"Paragraph {i}. " + "filler text " * 30 for i in range(20))
    chunks = chunk_text(long_text)
    assert all(c.content.strip() for c in chunks)


def test_long_freeform_text_splits_with_overlap() -> None:
    # One long, un-punctuated paragraph forces the sliding-window splitter.
    long_text = " ".join(f"word{i}" for i in range(3000))

    chunks = chunk_text(long_text, target_tokens=100, overlap_tokens=20)

    assert len(chunks) > 1
    for i in range(len(chunks) - 1):
        tail = chunks[i].content[-40:].strip()
        # the tail of chunk i should reappear near the start of chunk i+1
        assert tail[-20:] in chunks[i + 1].content[:400]


def test_structured_cv_splits_on_sections() -> None:
    cv_text = (
        "EXPERIENCE\n\n"
        "Senior Backend Engineer at Acme Corp. " + "Built scalable APIs. " * 40 + "\n\n"
        "EDUCATION\n\n"
        "BS in Computer Science, State University. " + "Graduated with honors. " * 20
    )

    chunks = chunk_text(cv_text, target_tokens=80, overlap_tokens=10)

    assert len(chunks) >= 1
    # Every chunk that contains a header also contains the body text that
    # immediately follows it in the source - headers never end up orphaned.
    for chunk in chunks:
        if "EXPERIENCE" in chunk.content:
            assert "Senior Backend Engineer" in chunk.content
        if "EDUCATION" in chunk.content:
            assert "BS in Computer Science" in chunk.content


def test_free_form_notes_without_headers_still_chunk() -> None:
    notes = "\n\n".join(
        [
            "Interviewer asked about distributed systems experience.",
            "I mentioned the outage postmortem I led last year.",
            "They seemed interested in my incident response process.",
        ]
    )
    chunks = chunk_text(notes)
    assert len(chunks) == 1
    assert "distributed systems" in chunks[0].content
    assert "incident response" in chunks[0].content
