"""Schema loading and management utilities."""

import importlib.util
import json
import os
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from .utils import create_base_model


class SchemaRegistry:
    """Registry for loading and managing schemas from files."""

    def __init__(self):
        self._schemas: Dict[str, Dict[str, Type[BaseModel]]] = {}

    def load_schema(
        self, name: str, file_path: str, base_path: Optional[str] = None
    ) -> Dict[str, Type[BaseModel]]:
        """
        Load a schema from a file.

        :param name: Name of the schema
        :param file_path: Path to the schema file
        :param base_path: Base path to resolve relative paths
        :return: Dictionary mapping model names to BaseModel classes
        """
        if base_path:
            file_path = os.path.join(base_path, file_path)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Schema file not found: {file_path}")

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".json":
            return self._load_json_schema(name, file_path)
        elif file_ext == ".py":
            return self._load_python_schema(name, file_path)
        else:
            raise ValueError(f"Unsupported schema file type: {file_ext}")

    def _load_json_schema(self, name: str, file_path: str) -> Dict[str, Type[BaseModel]]:
        """Load schema from JSON file."""
        with open(file_path, "r") as f:
            schema_data = json.load(f)

        models = {}

        # Handle root level schema
        if "properties" in schema_data:
            # Create a model for the root schema
            model = self._json_schema_to_pydantic(schema_data)
            models[name] = model

            # Also create models for individual properties if they are objects
            for prop_name, prop_schema in schema_data.get("properties", {}).items():
                if prop_schema.get("type") == "object" and "properties" in prop_schema:
                    prop_model = self._json_schema_to_pydantic(prop_schema)
                    models[prop_name] = prop_model

        # Handle definitions
        if "definitions" in schema_data:
            for def_name, def_schema in schema_data["definitions"].items():
                model = self._json_schema_to_pydantic(def_schema)
                models[def_name] = model

        self._schemas[name] = models
        return models

    def _json_schema_to_pydantic(self, schema: Dict[str, Any]) -> Type[BaseModel]:
        """Convert JSON schema to Pydantic BaseModel."""
        fields = {}

        if "properties" in schema:
            required = schema.get("required", [])
            for prop_name, prop_schema in schema["properties"].items():
                field_type = self._json_type_to_python(prop_schema)
                default_val = ... if prop_name in required else None
                description = prop_schema.get("description", "")

                if description:
                    field_info = {
                        "type": field_type,
                        "default": default_val,
                        "description": description,
                    }
                else:
                    field_info = {"type": field_type, "default": default_val}

                fields[prop_name] = field_info

        return create_base_model("DynamicModel", fields)

    def _json_type_to_python(self, schema: Dict[str, Any]) -> Any:
        """Convert JSON schema type to Python type."""
        json_type = schema.get("type")

        if json_type == "string":
            return str
        elif json_type == "number":
            return float
        elif json_type == "integer":
            return int
        elif json_type == "boolean":
            return bool
        elif json_type == "object":
            if "properties" in schema:
                return self._json_schema_to_pydantic(schema)
            else:
                return Dict[str, Any]
        elif json_type == "array":
            if "items" in schema:
                item_type = self._json_type_to_python(schema["items"])
                return List[item_type]  # type: ignore
            else:
                return List[Any]
        else:
            return Any

    def _load_python_schema(self, name: str, file_path: str) -> Dict[str, Type[BaseModel]]:
        """Load schema from Python module."""
        spec = importlib.util.spec_from_file_location(name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load Python module: {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        models = {}

        # Find all BaseModel subclasses in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModel) and attr != BaseModel:
                models[attr_name] = attr

        self._schemas[name] = models
        return models

    def get_model(self, schema_name: str, model_name: str) -> Type[BaseModel]:
        """
        Get a model from the registry.

        :param schema_name: Name of the schema
        :param model_name: Name of the model
        :return: BaseModel class
        """
        if schema_name not in self._schemas:
            raise ValueError(f"Schema '{schema_name}' not found")

        schema_models = self._schemas[schema_name]
        if model_name not in schema_models:
            raise ValueError(f"Model '{model_name}' not found in schema '{schema_name}'")

        return schema_models[model_name]


# Global schema registry
schema_registry = SchemaRegistry()
