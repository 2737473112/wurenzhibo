"""Initial migration.

Revision ID: c28e0c3daa9f
Revises: 
Create Date: 2023-12-20 22:50:20.330124

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c28e0c3daa9f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=20), nullable=False),
    sa.Column('password', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('user_status',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('is_live_streaming', sa.Boolean(), nullable=True),
    sa.Column('is_danmaku_reply_enabled', sa.Boolean(), nullable=True),
    sa.Column('voice', sa.String(length=255), nullable=True),
    sa.Column('speech_speed', sa.Float(), nullable=True),
    sa.Column('broadcast_strategy', sa.String(length=255), nullable=True),
    sa.Column('ai_rewrite', sa.Boolean(), nullable=True),
    sa.Column('is_broadcasting', sa.Boolean(), nullable=True),
    sa.Column('current_audio_timestamp', sa.Float(), nullable=True),
    sa.Column('audio_playback_status', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('qa_library',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('speech_library',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('speech_library')
    op.drop_table('qa_library')
    op.drop_table('user_status')
    op.drop_table('user')
    # ### end Alembic commands ###