import os
import asyncio
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

from httpx import AsyncClient
import streamlit as st
from streamlit import session_state as ss
from motor.motor_asyncio import AsyncIOMotorClient

st.set_page_config(layout="wide")

API_HOST = "https://shivering-jillayne-vocaelis-2b8c53fa.koyeb.app"

@st.cache_resource
def initiate_mongo_client():
    mongo_client = AsyncIOMotorClient(os.environ['MONGODB_URI'])
    mongo_client.get_io_loop = asyncio.get_running_loop  # type: ignore[method-assign]
    mongo_db = mongo_client['vocaelis_development']
    return mongo_db

mongo_db = initiate_mongo_client()

async def login_user(email: str):
    async with AsyncClient() as client:
        response = await client.post(
            f"{API_HOST}/auth/student/bearer/login", 
            data={"username": email, "password": "7106Kcn_"}
        )
        return response.json()['access_token']


async def get_students_db():
    return await mongo_db.b2b_student.find({}, {"_id": 1, "first_name": 1, "email": 1}).to_list()

async def get_student_remaining_rights_db(student_id: ObjectId):
    return await mongo_db.remaining_rights.find_one({"_id": student_id}, {"daily_story_practice": 1,"_id": 0})

async def get_story_title_db(story_id: ObjectId):
    return await mongo_db.story.find_one({"_id": story_id}, {"title": 1, "_id": 0})

async def get_incomplete_assignments_db(student_id: ObjectId):
    assignments = await mongo_db.b2b_student_assignment.find({"student_id": student_id, "completed": False}, {"story_id": 1, "started": 1, "_id": 0, "deducts_practice_rights": 1, "due_date": 1}).to_list()
    return [{"story_title":await get_story_title_db(assignment['story_id']),"started": assignment['started'], "deducts_practice_rights": assignment['deducts_practice_rights'], "due_date": assignment['due_date']} for assignment in assignments]

async def get_completed_assignments_db(student_id: ObjectId):
    assignments = await mongo_db.b2b_student_assignment.find({"student_id": student_id, "completed": True}, {"story_id": 1, "_id": 0, "due_date": 1}).to_list()
    return [{"story_title":await get_story_title_db(assignment['story_id']), "due_date": assignment['due_date']} for assignment in assignments]

async def get_student_suggested_stories_db(student_id: ObjectId):
    suggested_stories = await mongo_db.suggested_story.find({"suggested_for_id": student_id}, {"story_id": 1, "_id": 0}).sort("_id", 1).to_list()
    return [await get_story_title_db(story['story_id']) for story in suggested_stories[:-1]]


async def get_student_remaining_rights_api(access_token: str):
    async with AsyncClient() as client:
        response = await client.get(
            f"{API_HOST}/student/remaining_rights",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return {"daily_story_practice": response.json()["daily_story_practice"]}


async def get_incomplete_assignments_api(access_token: str):
    async with AsyncClient() as client:
        response = await client.get(
            f"{API_HOST}/assignment/student/incomplete",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return [{"story_title":await get_story_title_db(ObjectId(assignment["story"]['id'])), "started": assignment["started"], "deducts_practice_rights": assignment["deducts_practice_rights"], "due_date": assignment["due_date"]} for assignment in response.json()]


async def get_completed_assignments_api(access_token: str):
    async with AsyncClient() as client:
        response = await client.get(
            f"{API_HOST}/assignment/student/completed",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return [{"story_title": await get_story_title_db(ObjectId(assignment["story"]['id'])), "due_date": assignment["due_date"]} for assignment in response.json()]


async def get_student_suggested_stories_api(access_token: str):
    async with AsyncClient() as client:
        response = await client.get(
            f"{API_HOST}/story/suggestions/student",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return [await get_story_title_db(ObjectId(story['id'])) for story in response.json()]

async def main() -> None:
    students = await get_students_db()

    student = st.selectbox("Select a student", students, format_func=lambda x: x['first_name'])
    access_token = await login_user(student['email'])

    data_cols = st.columns(2)

    coroutines = [
        get_student_remaining_rights_db(student['_id']),
        get_incomplete_assignments_db(student['_id']),
        get_completed_assignments_db(student['_id']),
        get_student_suggested_stories_db(student['_id']),
        get_student_remaining_rights_api(access_token),
        get_incomplete_assignments_api(access_token),
        get_completed_assignments_api(access_token),
        get_student_suggested_stories_api(access_token)
    ]

    results = await asyncio.gather(*coroutines)

    db_results = results[:4]
    api_results = results[4:]

    with data_cols[0].container(border=True):
        st.write("DB Data")
        st.write(db_results[0])  # remaining_rights

        with st.expander("Incomplete Assignments"):
            st.write(db_results[1])  # incomplete_assignments
        
        with st.expander("Completed Assignments"):
            st.write(db_results[2])  # completed_assignments

        with st.expander("Suggested Stories"):
            st.write(db_results[3])  # suggested_stories

    with data_cols[1].container(border=True):
        st.write("API Data")
        st.write(api_results[0])  # remaining_rights

        with st.expander("Incomplete Assignments"):
            st.write(api_results[1])  # incomplete_assignments
        
        with st.expander("Completed Assignments"):
            st.write(api_results[2])  # completed_assignments

        with st.expander("Suggested Stories"):
            st.write(api_results[3])  # suggested_stories

    if st.button("Refresh Data"):
        st.rerun()

if __name__ == "__main__":
    asyncio.run(main())
