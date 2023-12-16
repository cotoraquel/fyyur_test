"""Description of the changes1

Revision ID: a275174b7775
Revises: 9fc5e09b9d3c
Create Date: 2023-08-09 02:13:02.686144

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a275174b7775'
down_revision = '9fc5e09b9d3c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('artists', schema=None) as batch_op:
        batch_op.drop_column('city')

    with op.batch_alter_table('venues', schema=None) as batch_op:
        batch_op.drop_column('city')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('venues', schema=None) as batch_op:
        batch_op.add_column(sa.Column('city', sa.VARCHAR(length=120), autoincrement=False, nullable=False))

    with op.batch_alter_table('artists', schema=None) as batch_op:
        batch_op.add_column(sa.Column('city', sa.VARCHAR(length=120), autoincrement=False, nullable=False))

    # ### end Alembic commands ###