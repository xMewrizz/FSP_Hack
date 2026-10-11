from datetime import datetime, timezone
import re
from typing import Sequence
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import CandidateProfile
from app.models.candidate_activity import CandidateActivity
from app.models.candidate_specialization import CandidateSpecializationTrack
from app.models.employer import EmployerProfile
from app.models.employer_task import EmployerTask, EmployerTaskSubmission, TaskAttachment
from app.models.user import User
from app.models.vacancy import Vacancy
from app.schemas.employer_task import (
    CandidateActivityResponse,
    CandidateTaskResponse,
    EmployerTaskCreate,
    EmployerTaskResponse,
    EmployerTaskReviewRequest,
    EmployerTaskSubmissionCreate,
    EmployerTaskSubmissionResponse,
    EmployerTaskUpdate,
    TaskFileResponse,
)


def _check_auto_answer(candidate_ans: str, reference_ans: str) -> bool:
    """Проверка ответа кандидата на соответствие эталону."""
    c_clean = candidate_ans.strip()
    r_clean = reference_ans.strip()

    # 1. Прямое совпадение без учёта регистра
    if c_clean.casefold() == r_clean.casefold():
        return True

    # 2. Нормализация пробелов и переносов строк
    c_normalized = re.sub(r"\s+", " ", c_clean).casefold()
    r_normalized = re.sub(r"\s+", " ", r_clean).casefold()
    if c_normalized == r_normalized:
        return True

    # 3. Числовое совпадение с допуском
    try:
        c_num = float(c_clean.replace(",", "."))
        r_num = float(r_clean.replace(",", "."))
        if abs(c_num - r_num) < 1e-4:
            return True
    except ValueError:
        pass

    return False


def _task_files(files: list[TaskAttachment]) -> list[TaskFileResponse]:
    return [
        TaskFileResponse(id=item.id, file_name=item.file_name, download_url=f"/tasks/attachments/{item.id}")
        for item in files
    ]


class EmployerTaskService:
    @staticmethod
    async def create_task(
        db: AsyncSession, employer_profile_id: uuid.UUID, data: EmployerTaskCreate
    ) -> EmployerTaskResponse:
        if data.task_type == "auto_check":
            if not data.reference_answer or not data.reference_answer.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Для автоматической проверки необходимо указать эталонный ответ",
                )

        if data.vacancy_id is not None:
            vacancy = await db.scalar(
                select(Vacancy).where(
                    Vacancy.id == data.vacancy_id,
                    Vacancy.employer_id == employer_profile_id,
                )
            )
            if vacancy is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Указанная вакансия не найдена у текущего работодателя",
                )

        employer = await db.get(EmployerProfile, employer_profile_id)
        if employer is None:
            raise HTTPException(status_code=404, detail="Профиль работодателя не найден")
        attachments = []
        if data.attachment_ids:
            attachments = (await db.scalars(select(TaskAttachment).where(
                TaskAttachment.id.in_(data.attachment_ids),
                TaskAttachment.owner_user_id == employer.user_id,
                TaskAttachment.task_id.is_(None),
                TaskAttachment.submission_id.is_(None),
            ))).all()
            if len(attachments) != len(set(data.attachment_ids)):
                raise HTTPException(status_code=400, detail="Одно из вложений недоступно")

        task = EmployerTask(
            employer_id=employer_profile_id,
            vacancy_id=data.vacancy_id,
            title=data.title.strip(),
            description=data.description.strip(),
            task_type=data.task_type,
            reference_answer=data.reference_answer.strip() if data.reference_answer else None,
            max_score=data.max_score,
            specialization=data.specialization,
            min_grade=data.min_grade,
            max_grade=data.max_grade,
            evaluation_criteria=[item.strip() for item in data.evaluation_criteria],
            resource_links=data.resource_links,
            is_active=True,
        )
        db.add(task)
        await db.flush()
        for attachment in attachments:
            attachment.task_id = task.id
        await db.commit()
        await db.refresh(task)

        return EmployerTaskResponse(
            id=task.id,
            employer_id=task.employer_id,
            vacancy_id=task.vacancy_id,
            company_name=employer.company_name if employer else None,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            reference_answer=task.reference_answer,
            max_score=task.max_score,
            specialization=task.specialization,
            min_grade=task.min_grade,
            max_grade=task.max_grade,
            evaluation_criteria=task.evaluation_criteria or [],
            resource_links=task.resource_links or [],
            is_platform_task=task.is_platform_task,
            attachments=_task_files(attachments),
            is_active=task.is_active,
            submissions_count=0,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    async def get_employer_tasks(
        db: AsyncSession, employer_profile_id: uuid.UUID
    ) -> list[EmployerTaskResponse]:
        employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.id == employer_profile_id))
        tasks = (await db.scalars(
            select(EmployerTask)
            .options(
                selectinload(EmployerTask.submissions),
                selectinload(EmployerTask.attachments),
            )
            .where(EmployerTask.employer_id == employer_profile_id)
            .order_by(EmployerTask.created_at.desc())
        )).all()

        return [
            EmployerTaskResponse(
                id=t.id,
                employer_id=t.employer_id,
                vacancy_id=t.vacancy_id,
                company_name=employer.company_name if employer else None,
                title=t.title,
                description=t.description,
                task_type=t.task_type,
                reference_answer=t.reference_answer,
                max_score=t.max_score,
                specialization=t.specialization,
                min_grade=t.min_grade,
                max_grade=t.max_grade,
                evaluation_criteria=t.evaluation_criteria or [],
                resource_links=t.resource_links or [],
                is_platform_task=t.is_platform_task,
                attachments=_task_files(t.attachments),
                is_active=t.is_active,
                submissions_count=len(t.submissions),
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tasks
        ]

    @staticmethod
    async def get_task_by_id_for_employer(
        db: AsyncSession, employer_profile_id: uuid.UUID, task_id: uuid.UUID
    ) -> EmployerTaskResponse:
        employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.id == employer_profile_id))
        task = await db.scalar(
            select(EmployerTask)
            .options(
                selectinload(EmployerTask.submissions),
                selectinload(EmployerTask.attachments),
            )
            .where(EmployerTask.id == task_id, EmployerTask.employer_id == employer_profile_id)
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")


        return EmployerTaskResponse(
            id=task.id,
            employer_id=task.employer_id,
            vacancy_id=task.vacancy_id,
            company_name=employer.company_name if employer else None,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            reference_answer=task.reference_answer,
            max_score=task.max_score,
            specialization=task.specialization,
            min_grade=task.min_grade,
            max_grade=task.max_grade,
            evaluation_criteria=task.evaluation_criteria or [],
            resource_links=task.resource_links or [],
            is_platform_task=task.is_platform_task,
            attachments=_task_files(task.attachments),
            is_active=task.is_active,
            submissions_count=len(task.submissions),
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    async def update_task(
        db: AsyncSession,
        employer_profile_id: uuid.UUID,
        task_id: uuid.UUID,
        data: EmployerTaskUpdate,
    ) -> EmployerTaskResponse:
        task = await db.scalar(
            select(EmployerTask)
            .options(
                selectinload(EmployerTask.submissions),
                selectinload(EmployerTask.attachments),
            )
            .where(EmployerTask.id == task_id, EmployerTask.employer_id == employer_profile_id)
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")

        if data.title is not None:
            task.title = data.title.strip()
        if data.description is not None:
            task.description = data.description.strip()
        if data.reference_answer is not None:
            task.reference_answer = data.reference_answer.strip()
        if data.max_score is not None:
            task.max_score = data.max_score
        if data.is_active is not None:
            task.is_active = data.is_active

        await db.commit()
        await db.refresh(task)

        employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.id == employer_profile_id))
        return EmployerTaskResponse(
            id=task.id,
            employer_id=task.employer_id,
            vacancy_id=task.vacancy_id,
            company_name=employer.company_name if employer else None,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            reference_answer=task.reference_answer,
            max_score=task.max_score,
            specialization=task.specialization,
            min_grade=task.min_grade,
            max_grade=task.max_grade,
            evaluation_criteria=task.evaluation_criteria or [],
            resource_links=task.resource_links or [],
            is_platform_task=task.is_platform_task,
            attachments=_task_files(task.attachments),
            is_active=task.is_active,
            submissions_count=len(task.submissions),
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    async def get_task_submissions(
        db: AsyncSession, employer_profile_id: uuid.UUID, task_id: uuid.UUID
    ) -> list[EmployerTaskSubmissionResponse]:
        task = await db.scalar(
            select(EmployerTask).where(
                EmployerTask.id == task_id, EmployerTask.employer_id == employer_profile_id
            )
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")

        submissions = (await db.scalars(
            select(EmployerTaskSubmission)
            .options(
                selectinload(EmployerTaskSubmission.candidate),
                selectinload(EmployerTaskSubmission.attachments),
            )
            .where(EmployerTaskSubmission.task_id == task_id)
            .order_by(EmployerTaskSubmission.created_at.desc())
        )).all()

        return [
            EmployerTaskSubmissionResponse(
                id=s.id,
                task_id=s.task_id,
                task_title=task.title,
                candidate_id=s.candidate_id,
                candidate_name=f"{s.candidate.first_name} {s.candidate.last_name}".strip() if s.candidate else None,
                answer_text=s.answer_text,
                answer_links=s.answer_links or [],
                contact_consent=s.contact_consent,
                attachments=_task_files(s.attachments),
                status=s.status,
                score=s.score,
                max_score=s.max_score,
                passed=s.passed,
                feedback=s.feedback,
                reviewed_by_user_id=s.reviewed_by_user_id,
                reviewed_at=s.reviewed_at,
                created_at=s.created_at,
            )
            for s in submissions
        ]

    @staticmethod
    async def review_submission(
        db: AsyncSession,
        employer_profile_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        submission_id: uuid.UUID,
        data: EmployerTaskReviewRequest,
    ) -> EmployerTaskSubmissionResponse:
        submission = await db.scalar(
            select(EmployerTaskSubmission)
            .options(
                selectinload(EmployerTaskSubmission.task),
                selectinload(EmployerTaskSubmission.candidate),
                selectinload(EmployerTaskSubmission.attachments),
            )
            .where(EmployerTaskSubmission.id == submission_id)
        )
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Решение не найдено")

        task = submission.task
        if task.employer_id != employer_profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Решение относится к заданию другой компании",
            )

        employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.id == employer_profile_id))
        company_name = employer.company_name if employer else "Работодатель"

        now = datetime.now(timezone.utc)
        final_score = min(data.score, submission.max_score)
        submission.score = final_score
        submission.passed = final_score / submission.max_score > 0.75
        submission.feedback = data.feedback
        submission.status = "graded"
        submission.reviewed_by_user_id = reviewer_user_id
        submission.reviewed_at = now

        # Обновляем активность кандидата (B-29)
        candidate = submission.candidate
        if candidate:
            if final_score / submission.max_score > 0.75:
                candidate.last_active_at = now
            status_text = "зачтено" if submission.passed else "не зачтено"
            activity = CandidateActivity(
                candidate_id=candidate.id,
                activity_type="employer_task_reviewed",
                title=f"Задание «{task.title}» проверено компанией {company_name}",
                description=f"Результат: {status_text}, балл: {final_score:.1f}/{submission.max_score:.1f}. {data.feedback or ''}".strip(),
                reference_id=submission.id,
            )
            db.add(activity)

        await db.commit()
        await db.refresh(submission)

        return EmployerTaskSubmissionResponse(
            id=submission.id,
            task_id=submission.task_id,
            task_title=task.title,
            candidate_id=submission.candidate_id,
            candidate_name=f"{candidate.first_name} {candidate.last_name}".strip() if candidate else None,
            answer_text=submission.answer_text,
            answer_links=submission.answer_links or [],
            contact_consent=submission.contact_consent,
            attachments=_task_files(submission.attachments),
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            passed=submission.passed,
            feedback=submission.feedback,
            reviewed_by_user_id=submission.reviewed_by_user_id,
            reviewed_at=submission.reviewed_at,
            created_at=submission.created_at,
        )

    # Candidate Methods
    @staticmethod
    async def list_tasks_for_candidate(
        db: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> list[CandidateTaskResponse]:
        candidate = await db.get(CandidateProfile, candidate_profile_id)
        if candidate is None:
            return []
        tracks = (await db.scalars(select(CandidateSpecializationTrack).where(
            CandidateSpecializationTrack.candidate_profile_id == candidate_profile_id,
        ))).all()
        track_by_specialization = {track.specialization: track for track in tracks}
        tasks = (await db.scalars(
            select(EmployerTask)
            .options(
                selectinload(EmployerTask.employer),
                selectinload(EmployerTask.attachments),
            )
            .where(EmployerTask.is_active.is_(True))
            .order_by(EmployerTask.created_at.desc())
        )).all()
        grade_order = ("junior", "middle", "senior", "lead")

        def is_available(task: EmployerTask) -> bool:
            if task.specialization is None:
                return True
            if task.specialization == candidate.specialization:
                grade = candidate.verified_grade or candidate.declared_grade
            elif task.specialization in track_by_specialization:
                grade = track_by_specialization[task.specialization].verified_grade
                if grade not in grade_order:
                    return False
            else:
                return False
            if task.min_grade is None or task.max_grade is None:
                return True
            if grade not in grade_order:
                return False
            return grade_order.index(task.min_grade) <= grade_order.index(grade) <= grade_order.index(task.max_grade)

        tasks = [task for task in tasks if is_available(task)]

        if not tasks:
            return []

        task_ids = [t.id for t in tasks]
        my_submissions = (await db.scalars(
            select(EmployerTaskSubmission)
            .options(selectinload(EmployerTaskSubmission.attachments))
            .where(
                EmployerTaskSubmission.candidate_id == candidate_profile_id,
                EmployerTaskSubmission.task_id.in_(task_ids),
            )
        )).all()
        sub_by_task = {s.task_id: s for s in my_submissions}

        items = []
        for t in tasks:
            sub = sub_by_task.get(t.id)
            sub_resp = None
            if sub:
                sub_resp = EmployerTaskSubmissionResponse(
                    id=sub.id,
                    task_id=sub.task_id,
                    task_title=t.title,
                    candidate_id=candidate_profile_id,
                    candidate_name=None,
                    answer_text=sub.answer_text,
                    answer_links=sub.answer_links or [],
                    contact_consent=sub.contact_consent,
                    attachments=_task_files(sub.attachments),
                    status=sub.status,
                    score=sub.score,
                    max_score=sub.max_score,
                    passed=sub.passed,
                    feedback=sub.feedback,
                    reviewed_by_user_id=sub.reviewed_by_user_id,
                    reviewed_at=sub.reviewed_at,
                    created_at=sub.created_at,
                )
            items.append(
                CandidateTaskResponse(
                    id=t.id,
                    employer_id=t.employer_id,
                    vacancy_id=t.vacancy_id,
                    company_name=t.employer.company_name if t.employer else "Работодатель",
                    title=t.title,
                    description=t.description,
                    task_type=t.task_type,
                    max_score=t.max_score,
                    specialization=t.specialization,
                    min_grade=t.min_grade,
                    max_grade=t.max_grade,
                    evaluation_criteria=t.evaluation_criteria or [],
                    resource_links=t.resource_links or [],
                    is_platform_task=t.is_platform_task,
                    attachments=_task_files(t.attachments),
                    created_at=t.created_at,
                    my_submission=sub_resp,
                )
            )
        return items

    @staticmethod
    async def get_task_for_candidate(
        db: AsyncSession, candidate_profile_id: uuid.UUID, task_id: uuid.UUID
    ) -> CandidateTaskResponse:
        task = await db.scalar(
            select(EmployerTask)
            .options(
                selectinload(EmployerTask.employer),
                selectinload(EmployerTask.attachments),
            )
            .where(EmployerTask.id == task_id, EmployerTask.is_active.is_(True))
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")

        if not any(item.id == task_id for item in await EmployerTaskService.list_tasks_for_candidate(db, candidate_profile_id)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание недоступно для вашего профиля")

        sub = await db.scalar(
            select(EmployerTaskSubmission)
            .options(selectinload(EmployerTaskSubmission.attachments))
            .where(
                EmployerTaskSubmission.task_id == task_id,
                EmployerTaskSubmission.candidate_id == candidate_profile_id,
            )
        )
        sub_resp = None
        if sub:
            sub_resp = EmployerTaskSubmissionResponse(
                id=sub.id,
                task_id=sub.task_id,
                task_title=task.title,
                candidate_id=candidate_profile_id,
                candidate_name=None,
                answer_text=sub.answer_text,
                answer_links=sub.answer_links or [],
                contact_consent=sub.contact_consent,
                attachments=_task_files(sub.attachments),
                status=sub.status,
                score=sub.score,
                max_score=sub.max_score,
                passed=sub.passed,
                feedback=sub.feedback,
                reviewed_by_user_id=sub.reviewed_by_user_id,
                reviewed_at=sub.reviewed_at,
                created_at=sub.created_at,
            )

        return CandidateTaskResponse(
            id=task.id,
            employer_id=task.employer_id,
            vacancy_id=task.vacancy_id,
            company_name=task.employer.company_name if task.employer else "Работодатель",
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            max_score=task.max_score,
            specialization=task.specialization,
            min_grade=task.min_grade,
            max_grade=task.max_grade,
            evaluation_criteria=task.evaluation_criteria or [],
            resource_links=task.resource_links or [],
            is_platform_task=task.is_platform_task,
            attachments=_task_files(task.attachments),
            created_at=task.created_at,
            my_submission=sub_resp,
        )

    @staticmethod
    async def submit_task_solution(
        db: AsyncSession,
        candidate_profile: CandidateProfile,
        task_id: uuid.UUID,
        data: EmployerTaskSubmissionCreate,
    ) -> EmployerTaskSubmissionResponse:
        if not any(
            item.id == task_id
            for item in await EmployerTaskService.list_tasks_for_candidate(db, candidate_profile.id)
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание недоступно для вашего профиля")
        task = await db.scalar(
            select(EmployerTask)
            .options(selectinload(EmployerTask.employer))
            .where(EmployerTask.id == task_id, EmployerTask.is_active.is_(True))
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено или закрыто")
        employer_user = await db.get(User, task.employer.user_id)
        if employer_user and not employer_user.is_active and employer_user.email.endswith("@example.test"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Это демонстрационное задание. Его можно изучить, но ответ здесь не проверяется работодателем.",
            )

        attachments = []
        if data.attachment_ids:
            attachments = (await db.scalars(select(TaskAttachment).where(
                TaskAttachment.id.in_(data.attachment_ids),
                TaskAttachment.owner_user_id == candidate_profile.user_id,
                TaskAttachment.task_id.is_(None),
                TaskAttachment.submission_id.is_(None),
            ))).all()
            if len(attachments) != len(set(data.attachment_ids)):
                raise HTTPException(status_code=400, detail="Одно из вложений недоступно")

        existing_sub = await db.scalar(
            select(EmployerTaskSubmission).where(
                EmployerTaskSubmission.task_id == task_id,
                EmployerTaskSubmission.candidate_id == candidate_profile.id,
            )
        )
        if existing_sub and existing_sub.status == "pending_review":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Предыдущее решение отправлено и ожидает проверки работодателем",
            )

        now = datetime.now(timezone.utc)
        company_name = task.employer.company_name if task.employer else "Работодатель"

        if task.task_type == "auto_check":
            reference = task.reference_answer or ""
            is_correct = _check_auto_answer(data.answer_text, reference)
            score = task.max_score if is_correct else 0.0
            status_str = "graded"
            feedback_str = (
                "Ответ совпал с эталонным решением."
                if is_correct
                else "Ответ не совпал с эталонным решением."
            )
            passed = is_correct
            reviewed_at = now
        else:
            # manual_review
            is_correct = None
            score = None
            status_str = "pending_review"
            feedback_str = "Ответ принят и ожидает оценки работодателем."
            passed = None
            reviewed_at = None

        if existing_sub:
            existing_sub.answer_text = data.answer_text.strip()
            existing_sub.answer_links = data.answer_links
            existing_sub.contact_consent = True
            existing_sub.status = status_str
            existing_sub.score = score
            existing_sub.max_score = task.max_score
            existing_sub.passed = passed
            existing_sub.feedback = feedback_str
            existing_sub.reviewed_at = reviewed_at
            existing_sub.reviewed_by_user_id = None
            submission = existing_sub
            for attachment in attachments:
                attachment.submission_id = existing_sub.id
        else:
            submission = EmployerTaskSubmission(
                task_id=task.id,
                candidate_id=candidate_profile.id,
                answer_text=data.answer_text.strip(),
                answer_links=data.answer_links,
                contact_consent=True,
                status=status_str,
                score=score,
                max_score=task.max_score,
                passed=passed,
                feedback=feedback_str,
                reviewed_at=reviewed_at,
            )
            db.add(submission)
            await db.flush()
            for attachment in attachments:
                attachment.submission_id = submission.id

        # Обновление сведений об активности кандидата (B-29)
        if task.task_type == "auto_check":
            if score / task.max_score > 0.75:
                candidate_profile.last_active_at = now
            activity_type = "employer_task_completed"
            activity_title = f"Выполнено задание «{task.title}» компании {company_name}"
            activity_desc = f"Автопроверка: {'успешно' if passed else 'неверный ответ'} (балл: {score:.1f}/{task.max_score:.1f})"
        else:
            activity_type = "employer_task_submitted"
            activity_title = f"Отправлено решение задания «{task.title}» компании {company_name}"
            activity_desc = "Ожидает ручной проверки работодателем"

        activity = CandidateActivity(
            candidate_id=candidate_profile.id,
            activity_type=activity_type,
            title=activity_title,
            description=activity_desc,
            reference_id=submission.id,
        )
        db.add(activity)

        await db.commit()
        await db.refresh(submission)

        return EmployerTaskSubmissionResponse(
            id=submission.id,
            task_id=submission.task_id,
            task_title=task.title,
            candidate_id=candidate_profile.id,
            candidate_name=f"{candidate_profile.first_name} {candidate_profile.last_name}".strip(),
            answer_text=submission.answer_text,
            answer_links=submission.answer_links or [],
            contact_consent=submission.contact_consent,
            attachments=_task_files(attachments),
            status=submission.status,
            score=submission.score,
            max_score=submission.max_score,
            passed=submission.passed,
            feedback=submission.feedback,
            reviewed_by_user_id=submission.reviewed_by_user_id,
            reviewed_at=submission.reviewed_at,
            created_at=submission.created_at,
        )

    @staticmethod
    async def get_candidate_submissions(
        db: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> list[EmployerTaskSubmissionResponse]:
        submissions = (await db.scalars(
            select(EmployerTaskSubmission)
            .options(
                selectinload(EmployerTaskSubmission.task),
                selectinload(EmployerTaskSubmission.attachments),
            )
            .where(EmployerTaskSubmission.candidate_id == candidate_profile_id)
            .order_by(EmployerTaskSubmission.created_at.desc())
        )).all()

        return [
            EmployerTaskSubmissionResponse(
                id=s.id,
                task_id=s.task_id,
                task_title=s.task.title if s.task else None,
                candidate_id=candidate_profile_id,
                candidate_name=None,
                answer_text=s.answer_text,
                answer_links=s.answer_links or [],
                contact_consent=s.contact_consent,
                attachments=_task_files(s.attachments),
                status=s.status,
                score=s.score,
                max_score=s.max_score,
                passed=s.passed,
                feedback=s.feedback,
                reviewed_by_user_id=s.reviewed_by_user_id,
                reviewed_at=s.reviewed_at,
                created_at=s.created_at,
            )
            for s in submissions
        ]

    @staticmethod
    async def get_candidate_activities(
        db: AsyncSession, candidate_profile_id: uuid.UUID
    ) -> list[CandidateActivityResponse]:
        activities = (await db.scalars(
            select(CandidateActivity)
            .where(CandidateActivity.candidate_id == candidate_profile_id)
            .order_by(CandidateActivity.created_at.desc())
        )).all()

        return [
            CandidateActivityResponse(
                id=a.id,
                candidate_id=a.candidate_id,
                activity_type=a.activity_type,
                title=a.title,
                description=a.description,
                reference_id=a.reference_id,
                created_at=a.created_at,
            )
            for a in activities
        ]
