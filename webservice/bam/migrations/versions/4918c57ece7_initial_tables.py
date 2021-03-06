"""initial_tables

Revision ID: 4918c57ece7
Revises: None
Create Date: 2014-11-05 18:26:17.841382

"""

# revision identifiers, used by Alembic.
revision = '4918c57ece7'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('setting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('value', sa.String(length=100), nullable=False),
    sa.Column('data_type', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('project',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('repository_path', sa.Text(), nullable=False),
    sa.Column('upload_path', sa.Text(), nullable=False),
    sa.Column('picture', sa.String(length=80), nullable=True),
    sa.Column('creation_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=80), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('project')
    op.drop_table('setting')
    ### end Alembic commands ###
