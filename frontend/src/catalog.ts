// Единый справочник специализаций и грейдов (B-01).
// Канонический источник для: анкеты кандидата, потребности работодателя,
// фильтров банка и запуска теста. Должен повторять backend/app/core/catalog.py.
// Расхождение значений — баг, а не «особенность экрана».
//
// Правила MVP:
// - Грейд подтверждает ТОЛЬКО тест. Достижения ФСП на порядок влияют,
//   но грейд не подтверждают.
// - Тест доступен: Backend × junior/middle/senior.
// - Остальные специализации и lead из данных НЕ удалены, но для теста скрыты.

export const ALL_SPECIALIZATIONS: string[] = [
  "Backend",
  "Frontend",
  "Fullstack",
  "Mobile",
  "DevOps / SRE",
  "Data Science / ML",
  "QA / Testing",
  "System Programming / C++",
  "GameDev",
];

export const ALL_GRADES: Array<{ value: string; label: string }> = [
  { value: "junior", label: "Junior" },
  { value: "middle", label: "Middle" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
];

export const TESTABLE_SPECIALIZATIONS: string[] = ["Backend"];
export const TESTABLE_GRADES: string[] = ["junior", "middle", "senior"];

export const TEST_AVAILABILITY_HINT =
  "Сейчас тест доступен для Backend (Junior / Middle / Senior).";

export function normalizeGrade(value: string | null | undefined): string | null {
  if (!value) return null;
  const cleaned = value.trim().toLowerCase();
  return cleaned || null;
}

export function isTestablePair(
  specialization: string | null | undefined,
  grade: string | null | undefined,
): boolean {
  if (!specialization || !grade) return false;
  const spec = specialization.trim();
  const grd = normalizeGrade(grade);
  return (
    TESTABLE_SPECIALIZATIONS.includes(spec) &&
    (TESTABLE_GRADES as string[]).includes(grd ?? "")
  );
}
