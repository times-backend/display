from sqlalchemy import create_engine, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, Text
from helper_sheet import filter_df
from dotenv import load_dotenv
import os
load_dotenv()
USERNAME=os.getenv("USERNAME")
PASSWORD=os.getenv("PASSWORD")
HOST=os.getenv("HOST")
PORT=os.getenv("PORT")
DB=os.getenv("DB")

#engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/preset")
engine = create_engine(f"postgresql+psycopg2://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB}")

Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

class Placement(Base):
    __tablename__ = "placement"
    id = Column(Integer, primary_key=True)
    website = Column(Text, nullable=False)
    platform = Column(Text, nullable=False)
    section = Column(Text, nullable=False)
    geo = Column(Text, nullable=False)
    placement = Column(Text, nullable=False)
    ad_unit_type = Column(Text, nullable=False)
    ad_sizes = Column(Text, nullable=True)
    supported_innovations = Column(Text, nullable=True)
    placement_name = Column(Text, nullable=False)

placements = session.query(Placement).all()

df = filter_df(TAB = "Sheet1", sheet_url="https://docs.google.com/spreadsheets/d/1UqE8MXnYuoZVAA8c152JUsveWOyCEhgcaihHKegX-Ac/edit?")

all_results = []
for _, row in df.iterrows():
    ad_unit_type = row['Ad Unit Type'].strip().upper()   
    placement = row['Placement'].strip()
    website = row['Website'].strip()
    platform = row['platform'].strip().upper()           

    if '+' in row['Section']:
        sections = [s.strip() for s in row['Section'].split('+')]
        section_filter = Placement.section.in_(sections)
    else:
        section_filter = Placement.section == row['Section'].strip()
    print(sections)
    result = (
        session.query(Placement)
        .filter(
            Placement.ad_unit_type.ilike(ad_unit_type),
            Placement.placement.ilike(placement),
            Placement.website.ilike(website),
            Placement.platform.ilike(platform),
            section_filter
        )
        .all()
    )

    all_results.extend(result)

placement_names = [r.placement_name for r in all_results]
print(placement_names)
