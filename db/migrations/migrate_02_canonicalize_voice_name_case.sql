-- Canonicalize voice name casing to match SupertonicEngine.AVAILABLE_VOICES.
--
-- Rows written before voice_set / claim_voice started normalizing case can
-- carry values like 'tichro' that don't case-sensitively match the engine's
-- pre-cached style keys ('Tichro', 'M1', …). The engine fix in
-- tts/supertonic_engine.py now handles this at runtime, but tidying the
-- stored values prevents future ambiguity and makes /voice get show the
-- right thing.
--
-- Idempotent: the WHERE clauses match only rows whose value differs from
-- the canonical form, so a second run touches 0 rows. The canonical list
-- is the union of AVAILABLE_VOICES keys in tts/supertonic_engine.py — keep
-- both in sync when adding a new voice.

UPDATE super_tts.user_preferences AS p
SET voice_name = c.canonical_name
FROM (VALUES
    ('m1', 'M1'),
    ('m2', 'M2'),
    ('m3', 'M3'),
    ('m4', 'M4'),
    ('m5', 'M5'),
    ('f1', 'F1'),
    ('f2', 'F2'),
    ('f3', 'F3'),
    ('f4', 'F4'),
    ('f5', 'F5'),
    ('tichro', 'Tichro')
) AS c(lower_name, canonical_name)
WHERE LOWER(p.voice_name) = c.lower_name
  AND p.voice_name <> c.canonical_name;

UPDATE super_tts.voice_claims AS v
SET voice_id = c.canonical_name
FROM (VALUES
    ('m1', 'M1'),
    ('m2', 'M2'),
    ('m3', 'M3'),
    ('m4', 'M4'),
    ('m5', 'M5'),
    ('f1', 'F1'),
    ('f2', 'F2'),
    ('f3', 'F3'),
    ('f4', 'F4'),
    ('f5', 'F5'),
    ('tichro', 'Tichro')
) AS c(lower_name, canonical_name)
WHERE LOWER(v.voice_id) = c.lower_name
  AND v.voice_id <> c.canonical_name;
