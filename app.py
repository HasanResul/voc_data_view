import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from streamlit import session_state as ss
from motor.motor_asyncio import AsyncIOMotorClient

@st.cache_resource
def initiate_mongo_client():
    mongo_client = AsyncIOMotorClient(os.environ['MONGODB_URI'])
    mongo_client.get_io_loop = asyncio.get_running_loop  # type: ignore[method-assign]
    mongo_db = mongo_client['vocaelis_development']
    return mongo_db

mongo_db = initiate_mongo_client()

async def get_students_db():
    return await mongo_db.b2b_student.find({}, {"_id": 1, "first_name": 1}).to_list()

async def get_student_remaining_rights_db(student_id: str):
    return await mongo_db.remaining_rights.find_one({"_id": student_id}, {"daily_story_practice": 1,"_id": 0})

async def get_story_title_db(story_id: str):
    return await mongo_db.story.find_one({"_id": story_id}, {"title": 1, "_id": 0})

async def get_incomplete_assignments_db(student_id: str):
    assignments = await mongo_db.b2b_student_assignment.find({"student_id": student_id, "completed": False}, {"story_id": 1, "started": 1, "_id": 0, "deducts_practice_rights": 1, "due_date": 1}).to_list()
    return [{"story_title":await get_story_title_db(assignment['story_id']),"started": assignment['started'], "deducts_practice_rights": assignment['deducts_practice_rights'], "due_date": assignment['due_date']} for assignment in assignments]

async def get_completed_assignments_db(student_id: str):
    assignments = await mongo_db.b2b_student_assignment.find({"student_id": student_id, "completed": True}, {"story_id": 1, "_id": 0, "deducts_practice_rights": 1, "due_date": 1}).to_list()
    return [{"story_title":await get_story_title_db(assignment['story_id']), "deducts_practice_rights": assignment['deducts_practice_rights'], "due_date": assignment['due_date']} for assignment in assignments]

async def get_student_suggested_stories_db(student_id: str):
    suggested_stories = await mongo_db.suggested_story.find({"suggested_for_id": student_id}, {"story_id": 1, "_id": 0}).sort("_id", 1).to_list()
    return [await get_story_title_db(story['story_id']) for story in suggested_stories[:-1]]

async def main() -> None:
    students = await get_students_db()

    student = st.selectbox("Select a student", students, format_func=lambda x: x['first_name'])

    remaining_rights = await get_student_remaining_rights_db(student['_id'])
    st.write(remaining_rights)

    incomplete_assignments = await get_incomplete_assignments_db(student['_id'])
    with st.expander("Incomplete Assignments"):
        st.write(incomplete_assignments)
    
    completed_assignments = await get_completed_assignments_db(student['_id'])
    with st.expander("Completed Assignments"):
        st.write(completed_assignments)

    suggested_stories = await get_student_suggested_stories_db(student['_id'])
    with st.expander("Suggested Stories"):
        st.write(suggested_stories)

if __name__ == "__main__":
    asyncio.run(main())
