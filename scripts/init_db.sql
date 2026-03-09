create table if not exists public.students (
  id text primary key,
  required_credits integer not null default 128,
  updated_at timestamptz not null default now()
);

create table if not exists public.enrollments (
  id bigserial primary key,
  student_id text not null references public.students(id) on delete cascade,
  course_id text not null,
  credits integer not null default 0,
  passed boolean not null default false,
  grade text,
  created_at timestamptz not null default now()
);

create index if not exists idx_enrollments_student_id
  on public.enrollments(student_id);

create index if not exists idx_enrollments_student_course
  on public.enrollments(student_id, course_id);