"""Ordered registry of Atlas schema migrations.

Each migration is one module in this package exporting:

- ``VERSION``: unique integer version, contiguous starting at 1
- ``NAME``: short human-readable migration name
- ``apply(connection)``: deterministic, additive schema change

``apply(connection)`` runs inside a transaction owned by the migration runner
(`database.migrator`), so a migration must not call ``connection.commit()`` or
``connection.rollback()`` itself; the runner commits the migration together
with its ledger record, or rolls both back on failure.

Register migrations in ``MIGRATIONS`` in version order. The runner validates
the registry on every run and refuses duplicate or non-contiguous versions.
"""

from database.migrations import (
    migration_001_baseline,
    migration_002_additive_columns,
    migration_003_risk_decisions,
    migration_004_stabilization_evidence,
    migration_005_outcome_tracking,
)

MIGRATIONS = [
    migration_001_baseline,
    migration_002_additive_columns,
    migration_003_risk_decisions,
    migration_004_stabilization_evidence,
    migration_005_outcome_tracking,
]


def validate_migrations(migrations):
    """Return the migrations sorted by version, failing loudly on a bad registry."""
    validated = list(migrations)

    for migration in validated:
        version = getattr(migration, "VERSION", None)
        name = getattr(migration, "NAME", None)
        apply_callable = getattr(migration, "apply", None)

        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ValueError(
                f"Migration {migration!r} must define an integer VERSION >= 1."
            )
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Migration version {version} must define a non-empty string NAME."
            )
        if not callable(apply_callable):
            raise ValueError(
                f"Migration version {version} ({name}) must define a callable "
                "apply(connection)."
            )

    validated.sort(key=lambda migration: migration.VERSION)
    versions = [migration.VERSION for migration in validated]

    duplicates = sorted({v for v in versions if versions.count(v) > 1})
    if duplicates:
        raise ValueError(
            f"Duplicate migration versions are not allowed: {duplicates}. "
            "Every migration must have a unique version number."
        )

    expected = list(range(1, len(versions) + 1))
    if versions != expected:
        raise ValueError(
            "Migration versions must be contiguous starting at 1; "
            f"got {versions}, expected {expected}."
        )

    return validated
