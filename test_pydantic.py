from pydantic import BaseModel, Field, ConfigDict
class FileMetadata(BaseModel):
    id: str = Field(alias='_id')
doc = {'_id': '123'}
try:
    print(FileMetadata(**doc))
except Exception as e:
    print('Error:', e)
