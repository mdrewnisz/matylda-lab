# Notebook: Operacje lokalne w silosie Legal

status: local_silo_only
source_scope: vault/legal/2024-2026
raw_content_policy: do_not_copy_source_text
executor_policy: manual_only
legal_advice: false
human_review: required

## Zasada główna

Materiały Legal pozostają w `vault/legal`. Skills, notebooks, templates, manifesty i handoffy Legal również pozostają w `vault/legal`.

## Dozwolone na obecnym etapie

- metadata intake;
- hash pliku;
- klasyfikacja po nazwie/rozszerzeniu;
- ręczny handoff do review;
- wzorce konstrukcyjne bez danych sprawy.

## Niedozwolone na obecnym etapie

- streszczanie akt przez LLM;
- kopiowanie treści do `data/memory`, `data/knowledge`, globalnych `skills/` lub globalnych `notebooks/`;
- interpretacja prawna bez człowieka;
- generowanie pisma do wysyłki jako finalnego;
- eksport surowych danych poza lokalny vault.

## Następny bezpieczny krok

Dodać ręczną klasyfikację dokumentów w manifestach: `document_role`, `case_phase`, `review_status`, `usable_for_draft`.
