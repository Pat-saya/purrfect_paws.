-- Stage 2: keep the existing cat rows and their database IDs while preparing
-- one breeds table for cats and dogs.
-- Run with psql. ON_ERROR_STOP makes psql stop at the first failed check;
-- disconnecting with an open transaction rolls all table changes back.
\set ON_ERROR_STOP on
BEGIN;

-- Refuse the wrong database or a second run before changing any table.
DO $$
BEGIN
    IF current_database() <> 'purrfect_paws' THEN
        RAISE EXCEPTION 'Expected database purrfect_paws';
    END IF;
    IF to_regclass('cat_breeds') IS NULL THEN
        RAISE EXCEPTION 'Expected cat_breeds table is missing';
    END IF;
    IF to_regclass('breeds') IS NOT NULL THEN
        RAISE EXCEPTION 'breeds already exists; migration has already run or database is unexpected';
    END IF;
    IF (SELECT COUNT(*) FROM cat_breeds) <> 106 THEN
        RAISE EXCEPTION 'Expected exactly 106 cat breeds';
    END IF;
    IF (SELECT COUNT(*) FROM user_questionnaires) <> 8 THEN
        RAISE EXCEPTION 'Expected exactly 8 questionnaires';
    END IF;
    IF EXISTS (
        SELECT 1 FROM user_questionnaires q
        LEFT JOIN cat_breeds b ON b.id = q.matched_breed_id
        WHERE q.matched_breed_id IS NOT NULL AND b.id IS NULL
    ) THEN
        RAISE EXCEPTION 'A questionnaire refers to a missing cat breed';
    END IF;
    IF EXISTS (
        SELECT 1 FROM quiz_results r
        LEFT JOIN cat_breeds b ON b.id = r.breed_id
        WHERE r.breed_id IS NOT NULL AND b.id IS NULL
    ) THEN
        RAISE EXCEPTION 'A quiz result refers to a missing cat breed';
    END IF;
END $$;

-- Temporary snapshots let us compare the original IDs and answers before COMMIT.
-- They disappear when the psql session ends; they are not application tables.
CREATE TEMP TABLE stage2_original_breed_ids AS
SELECT id FROM cat_breeds;
CREATE TEMP TABLE stage2_original_questionnaires AS
SELECT id, answers::text AS answers_text, matched_breed_id
FROM user_questionnaires;

-- Renaming keeps each breed row's ID and its existing foreign-key targets.
ALTER TABLE cat_breeds RENAME TO breeds;

-- The old image_url values are API breed IDs, not URLs. Keep every value,
-- then create a separate nullable field for a real image URL.
ALTER TABLE breeds RENAME COLUMN image_url TO api_breed_id;
ALTER TABLE breeds ADD COLUMN image_url VARCHAR(500);

-- Backfill cats before requiring a species on every breed.
ALTER TABLE breeds ADD COLUMN species VARCHAR(10);
UPDATE breeds SET species = 'cat';
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM breeds WHERE species = 'cat') <> 106 THEN
        RAISE EXCEPTION 'Breed species backfill did not cover all 106 cats';
    END IF;
END $$;
ALTER TABLE breeds ALTER COLUMN species SET NOT NULL;
ALTER TABLE breeds ADD CONSTRAINT breeds_species_check
    CHECK (species IN ('cat', 'dog'));

-- Existing questionnaires were all for cats. Backfill before NOT NULL.
ALTER TABLE user_questionnaires ADD COLUMN species VARCHAR(10);
UPDATE user_questionnaires SET species = 'cat';
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM user_questionnaires WHERE species = 'cat') <> 8 THEN
        RAISE EXCEPTION 'Questionnaire species backfill did not cover all 8 rows';
    END IF;
END $$;
ALTER TABLE user_questionnaires ALTER COLUMN species SET NOT NULL;
ALTER TABLE user_questionnaires ADD CONSTRAINT user_questionnaires_species_check
    CHECK (species IN ('cat', 'dog'));

-- API IDs are required for both species. Check old values before enforcing
-- uniqueness within each species; the same API ID may exist in both APIs.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM breeds WHERE api_breed_id IS NULL OR api_breed_id = '') THEN
        RAISE EXCEPTION 'An existing cat breed has no API breed ID';
    END IF;
    IF EXISTS (
        SELECT 1 FROM breeds
        GROUP BY species, api_breed_id HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existing API breed IDs are not unique within species';
    END IF;
END $$;
ALTER TABLE breeds ALTER COLUMN api_breed_id SET NOT NULL;
ALTER TABLE breeds ADD CONSTRAINT breeds_species_api_breed_id_key
    UNIQUE (species, api_breed_id);

-- Final checks: original rows and answers must be unchanged, and both
-- foreign keys must still point to breeds. Do not call nextval merely to test
-- the sequence, because that would consume an ID.
DO $$
DECLARE
    sequence_name TEXT;
    sequence_last BIGINT;
    sequence_called BOOLEAN;
    sequence_increment BIGINT;
    next_id BIGINT;
BEGIN
    IF (SELECT COUNT(*) FROM breeds) <> 106
       OR (SELECT COUNT(*) FROM stage2_original_breed_ids) <> 106
       OR EXISTS (
           SELECT 1 FROM stage2_original_breed_ids old
           FULL JOIN breeds b ON b.id = old.id
           WHERE old.id IS NULL OR b.id IS NULL
       ) THEN
        RAISE EXCEPTION 'Breed IDs or row count changed';
    END IF;
    IF (SELECT COUNT(*) FROM breeds WHERE species = 'cat') <> 106 THEN
        RAISE EXCEPTION 'An original breed is not marked cat';
    END IF;
    IF (SELECT COUNT(*) FROM user_questionnaires) <> 8
       OR (SELECT COUNT(*) FROM stage2_original_questionnaires) <> 8
       OR EXISTS (
           SELECT 1 FROM stage2_original_questionnaires old
           FULL JOIN user_questionnaires q ON q.id = old.id
           WHERE old.id IS NULL OR q.id IS NULL
              OR q.answers::text IS DISTINCT FROM old.answers_text
              OR q.matched_breed_id IS DISTINCT FROM old.matched_breed_id
       ) THEN
        RAISE EXCEPTION 'Questionnaire IDs, answers, or matches changed';
    END IF;
    IF (SELECT COUNT(*) FROM user_questionnaires WHERE species = 'cat') <> 8 THEN
        RAISE EXCEPTION 'An original questionnaire is not marked cat';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.contype = 'f'
          AND c.conrelid = 'user_questionnaires'::regclass
          AND c.confrelid = 'breeds'::regclass
          AND a.attname = 'matched_breed_id'
    ) THEN
        RAISE EXCEPTION 'Questionnaire match foreign key no longer references breeds';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.contype = 'f'
          AND c.conrelid = 'quiz_results'::regclass
          AND c.confrelid = 'breeds'::regclass
          AND a.attname = 'breed_id'
    ) THEN
        RAISE EXCEPTION 'Quiz result breed foreign key no longer references breeds';
    END IF;
    IF EXISTS (
        SELECT 1 FROM user_questionnaires q
        LEFT JOIN breeds b ON b.id = q.matched_breed_id
        WHERE q.matched_breed_id IS NOT NULL AND b.id IS NULL
    ) OR EXISTS (
        SELECT 1 FROM quiz_results r
        LEFT JOIN breeds b ON b.id = r.breed_id
        WHERE r.breed_id IS NOT NULL AND b.id IS NULL
    ) THEN
        RAISE EXCEPTION 'A breed reference became orphaned';
    END IF;

    sequence_name := pg_get_serial_sequence('breeds', 'id');
    IF sequence_name IS NULL THEN
        RAISE EXCEPTION 'Breeds ID sequence is missing';
    END IF;
    EXECUTE format('SELECT last_value, is_called FROM %s', sequence_name::regclass)
        INTO sequence_last, sequence_called;
    SELECT seqincrement INTO sequence_increment
    FROM pg_sequence WHERE seqrelid = sequence_name::regclass;
    IF sequence_increment IS NULL OR sequence_increment <= 0 THEN
        RAISE EXCEPTION 'Breeds ID sequence increment is invalid';
    END IF;
    next_id := sequence_last + CASE WHEN sequence_called THEN sequence_increment ELSE 0 END;
    IF next_id <= (SELECT MAX(id) FROM breeds) THEN
        RAISE EXCEPTION 'Next breed ID would collide with an existing breed';
    END IF;
END $$;

-- No table changes remain if any check above fails.
COMMIT;
