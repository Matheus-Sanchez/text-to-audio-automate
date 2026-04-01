from app.core.database import JobRepository
from app.core.models import JobStage, JobStatus


def test_job_repository_crud(tmp_path) -> None:
    repo = JobRepository(tmp_path / "app.db")
    job_id = repo.create_job(
        source_path="input.txt",
        source_hash="abc",
        source_type=".txt",
        status=JobStatus.PROCESSING,
        stage=JobStage.INGESTED,
    )
    repo.update_job(job_id, stage=JobStage.CLEANED, status=JobStatus.COMPLETED)
    job = repo.get_job(job_id)
    assert job is not None
    assert job.stage == JobStage.CLEANED
    assert job.status == JobStatus.COMPLETED
