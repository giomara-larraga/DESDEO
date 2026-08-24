from sqlmodel import Field, SQLModel


class GroupUserLink(SQLModel, table=True):
    __tablename__ = "group_user_link"

    group_id: int = Field(foreign_key="group.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)