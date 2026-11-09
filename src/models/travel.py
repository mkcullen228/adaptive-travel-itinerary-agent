from pydantic import BaseModel, Field
from typing import List


class TravelEstimate(BaseModel):
    """ """
    mode: str
    duration_minutes: int = Field(gt=0)
    source: str


class TravelLeg(BaseModel):
    """"""
    origin_activity_id: str
    destination_activity_id: str
    estimates: List[TravelEstimate]
    selected_mode: str


# ex_nested = TravelLeg(
#     origin_activity_id="activity_001",
#     destination_activity_id="activity_002",
#     estimates=[
#         TravelEstimate(
#             mode="walking",
#             duration_minutes=12,
#             source="manual_test_data",
#             ), 
#         TravelEstimate(
#             mode="driving",
#             duration_minutes=8,
#             source="manual_test_data",
#             )
#     ]
# )

# print(ex_nested)
