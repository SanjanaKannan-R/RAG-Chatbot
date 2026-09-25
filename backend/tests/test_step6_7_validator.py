import os
import tempfile
from app.db.session import init_db, get_db_connection, serialize_vector
from app.retrieval.embeddings import DeterministicLocalProvider
from app.ingestion.ingest_service import IngestionService
from app.generation.citation_validator import CitationValidator
from app.generation.prompt_templates import format_context_chunks, build_user_prompt, SYSTEM_PROMPT
from app.generation.llm_provider import GroundedRuleLLMProvider

def test_citation_validator_and_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_val.db")
        provider = DeterministicLocalProvider(dimension=64)
        init_db(db_path, embedding_dim=64)
        ingest_svc = IngestionService(db_path=db_path, embedding_provider=provider)

        # Ingest a real sample document
        doc_file = os.path.join(tmpdir, "benefits.txt")
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(
                "Health Insurance Benefits 2026\n"
                "Dental coverage covers up to $2,000 per year per dependent.\n"
                "Vision coverage includes one free annual exam and $150 frame allowance.\n"
            )

        ingest_res = ingest_svc.ingest_file(doc_file, "benefits.txt")
        assert ingest_res["status"] == "ready"

        conn = get_db_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, chunk_text FROM chunks WHERE document_id = ?", (ingest_res["document_id"],))
        rows = cur.fetchall()
        real_chunk_id = rows[0]["id"]
        real_chunk_text = rows[0]["chunk_text"]

        validator = CitationValidator(db_path=db_path)

        # 1. Test valid citation
        raw_valid = [
            {"chunk_id": real_chunk_id, "quoted_snippet": "Dental coverage covers up to $2,000"}
        ]
        grounded, validated, warning = validator.validate_citations(
            raw_citations=raw_valid,
            retrieved_chunk_ids=[real_chunk_id]
        )
        assert grounded is True
        assert len(validated) == 1
        assert validated[0].chunk_id == real_chunk_id
        assert validated[0].source_file == "benefits.txt"
        assert "Dental coverage" in validated[0].quoted_snippet
        assert validated[0].chunk_text == real_chunk_text
        print("Valid citation test passed.")

        # 2. Test hallucinated chunk_id (not in DB)
        raw_hallucinated = [
            {"chunk_id": 99999, "quoted_snippet": "Fake snippet"}
        ]
        grounded, validated, warning = validator.validate_citations(
            raw_citations=raw_hallucinated,
            retrieved_chunk_ids=[real_chunk_id]
        )
        assert grounded is False
        assert len(validated) == 0
        assert "grounded" in warning.lower()
        print("Hallucinated chunk_id (not in DB) correctly rejected.")

        # 3. Test unretrieved chunk_id (in DB, but NOT retrieved for this query)
        raw_unretrieved = [
            {"chunk_id": real_chunk_id, "quoted_snippet": "Dental coverage"}
        ]
        grounded, validated, warning = validator.validate_citations(
            raw_citations=raw_unretrieved,
            retrieved_chunk_ids=[888]  # not in retrieved set
        )
        assert grounded is False
        assert len(validated) == 0
        print("Unretrieved chunk_id correctly rejected.")

        # 4. Test mixed citations (one valid, one hallucinated)
        raw_mixed = [
            {"chunk_id": real_chunk_id, "quoted_snippet": "Vision coverage includes one free annual exam"},
            {"chunk_id": 404, "quoted_snippet": "Hallucinated claim"}
        ]
        grounded, validated, warning = validator.validate_citations(
            raw_citations=raw_mixed,
            retrieved_chunk_ids=[real_chunk_id]
        )
        assert grounded is True
        assert len(validated) == 1
        assert validated[0].chunk_id == real_chunk_id
        assert "Stripped 1 unverified" in warning
        print("Mixed citation pruning passed.")

        # 5. Test prompt formatting and generation
        chunks_for_prompt = [{
            "chunk_id": real_chunk_id,
            "source_file": "benefits.txt",
            "line_or_row_range": "lines 1-4",
            "chunk_text": real_chunk_text
        }]
        user_prompt = build_user_prompt("What does dental coverage cover?", chunks_for_prompt)
        assert f"[chunk_id: {real_chunk_id} | source: benefits.txt" in user_prompt

        llm = GroundedRuleLLMProvider()
        llm_output = llm.generate_cited_answer(SYSTEM_PROMPT, user_prompt)
        print("LLM raw output:", llm_output)
        assert "answer" in llm_output
        assert "citations" in llm_output

        # Validate LLM output with validator
        grounded, final_cites, warn = validator.validate_citations(
            raw_citations=llm_output["citations"],
            retrieved_chunk_ids=[real_chunk_id]
        )
        assert grounded is True
        assert len(final_cites) > 0
        print("End-to-end generation + validation pipeline passed!")

        conn.close()

if __name__ == "__main__":
    test_citation_validator_and_generation()
