from nomos import step, tool, Agent, Step
import requests
from typing import Dict, Optional, Literal, Annotated


class MasterRoshi(Agent):
    __persona__ = (
        "You are Master Roshi, a wise and humorous martial arts master from the Dragon Ball series. "
        "You are known for your playful and flirtatious nature, as well as your deep knowledge of martial arts. "
        "You enjoy teaching and guiding others, often with a mix of humor and wisdom. "
        "You have a strong sense of justice and are always ready to help those in need."
    )

    @tool
    def get_characters(
        page: Annotated[Optional[int], "Page number to retrieve"],
        name: Annotated[Optional[str], "Filter characters by name"],
        gender: Annotated[
            Optional[Literal["Male", "Female", "Other", "Unknown"]],
            "Filter characters by gender",
        ],
        race: Annotated[
            Optional[
                Literal[
                    "Saiyan",
                    "Namekian",
                    "Human",
                    "Majin",
                    "Frieza Race",
                    "Jiren Race",
                    "Android",
                    "God",
                    "Angel",
                    "Evil",
                    "Unknown",
                    "Nucleico benigno",
                    "Nucleico",
                ]
            ],
            "Filter characters by race",
        ],
        limit: Annotated[Optional[int], "Number of items per page"] = 10,
    ) -> Dict:
        """Get all characters if no params are provided."""
        url = "https://dragonball-api.com/api/characters"
        params = {
            "page": page,
            "name": name,
            "gender": gender,
            "race": race,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(url, params=params)
        return response.json()

    @tool
    def get_character_details(self, id: Annotated[int, "Character ID"]) -> Dict:
        """Get one character with origin planet and transformations."""
        url = f"https://dragonball-api.com/api/characters/{id}"
        response = requests.get(url)
        return response.json()

    @tool
    def get_planets(
        self,
        page: Annotated[Optional[int], "Page number to retrieve"],
        name: Annotated[Optional[str], "Filter planets by name"],
        isDestroyed: Annotated[Optional[bool], "Filter planets by destroyed status"],
        limit: Annotated[Optional[int], "Number of items per page"] = 10,
    ) -> Dict:
        """Get all planets if no params are provided."""
        url = "https://dragonball-api.com/api/planets"
        params = {
            "page": page,
            "name": name,
            "isDestroyed": isDestroyed,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = requests.get(url, params=params)
        return response.json()

    @tool
    def get_planet_characters(self, id: Annotated[int, "Planet ID"]) -> Dict:
        """Get Characters from a specific planet."""
        url = f"https://dragonball-api.com/api/planets/{id}"
        response = requests.get(url)
        return response.json()

    @step(start=True)
    def start_step(self) -> Step:
        return Step(
            step_id="start",
            description=(
                "Greet the user and Welcome to the Universe of Dragon Ball. "
                "Use the tools to provide information about characters and planets from the Dragon Ball series."
            ),
            available_tools=self.tools,
        )


agent = MasterRoshi()
app = agent.app

if __name__ == "__main__":
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)

    agent.run()
