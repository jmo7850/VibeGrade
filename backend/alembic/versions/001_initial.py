"""Initial migration - create all tables.

Revision ID: 001
Revises:
Create Date: 2026-10-11 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scans table
    op.create_table(
        'scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('repo_url', sa.String(500), nullable=False),
        sa.Column('repo_owner', sa.String(100), nullable=False),
        sa.Column('repo_name', sa.String(100), nullable=False),
        sa.Column('commit_sha', sa.String(40), nullable=False),
        sa.Column('branch', sa.String(200), nullable=False),
        sa.Column('project_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('rubric_version', sa.String(20), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scans_user_created', 'scans', ['user_id', 'created_at'])
    op.create_index('ix_scans_repo_commit', 'scans', ['repo_owner', 'repo_name', 'commit_sha'])
    op.create_index(op.f('ix_scans_status'), 'scans', ['status'])

    # Create checks table
    op.create_table(
        'checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('evidence_ref', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_checks_scan_id'), 'checks', ['scan_id'])

    # Create evidence_blobs table
    op.create_table(
        'evidence_blobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('check_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['check_id'], ['checks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evidence_blobs_check_id'), 'evidence_blobs', ['check_id'])

    # Create findings table
    op.create_table(
        'findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('check_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fingerprint', sa.String(200), nullable=False),
        sa.Column('tool', sa.String(50), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('line_start', sa.Integer(), nullable=False),
        sa.Column('line_end', sa.Integer(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_ref', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rubric_dimensions', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['check_id'], ['checks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_findings_scan_severity', 'findings', ['scan_id', 'severity'])
    op.create_index('ix_findings_scan_confidence', 'findings', ['scan_id', 'confidence'])
    op.create_index('ix_findings_fingerprint', 'findings', ['fingerprint'])

    # Create scores table
    op.create_table(
        'scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('coverage_percent', sa.Float(), nullable=False),
        sa.Column('confidence_percent', sa.Float(), nullable=False),
        sa.Column('grade', sa.String(2), nullable=False),
        sa.Column('readiness_verdict', sa.String(50), nullable=False),
        sa.Column('critical_blockers', sa.Integer(), nullable=False),
        sa.Column('dimension_scores', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scores_scan_id'), 'scores', ['scan_id'], unique=True)

    # Create rubric_versions table
    op.create_table(
        'rubric_versions',
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('version'),
    )


def downgrade() -> None:
    op.drop_table('rubric_versions')
    op.drop_table('scores')
    op.drop_table('findings')
    op.drop_table('evidence_blobs')
    op.drop_table('checks')
    op.drop_table('scans')
