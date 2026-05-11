import ifcopenshell
import pandas as pd
from typing import Optional


BUILDING_ELEMENT_TYPES = [
    "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn", "IfcBeam",
    "IfcDoor", "IfcWindow", "IfcRoof", "IfcStair", "IfcStairFlight",
    "IfcRailing", "IfcCovering", "IfcCurtainWall", "IfcPlate", "IfcMember",
    "IfcBuildingElementProxy", "IfcFlowSegment", "IfcFlowTerminal",
    "IfcFlowFitting", "IfcEnergyConversionDevice",
]


def parse_ifc_file(file_path: str) -> dict:
    try:
        model = ifcopenshell.open(file_path)
    except Exception as e:
        raise ValueError(f"IFC-Datei konnte nicht gelesen werden: {e}")

    element_to_storey = _build_storey_map(model)

    elements = extract_elements(model, element_to_storey)
    spaces = extract_spaces(model, element_to_storey)
    storeys = extract_storeys(model)
    metadata = get_model_metadata(model)

    return {
        "model": model,
        "elements": elements,
        "spaces": spaces,
        "storeys": storeys,
        "metadata": metadata,
        "schema": model.schema,
    }


def _build_storey_map(model) -> dict:
    element_to_storey = {}
    try:
        for rel in model.by_type("IfcRelContainedInSpatialStructure"):
            structure = rel.RelatingStructure
            if structure.is_a("IfcBuildingStorey"):
                storey_name = structure.Name or f"Geschoss {structure.id()}"
                for element in rel.RelatedElements:
                    element_to_storey[element.id()] = storey_name
    except Exception:
        pass
    return element_to_storey


def extract_elements(model, element_to_storey: dict) -> list[dict]:
    elements = []
    seen_ids = set()

    for ifc_type in BUILDING_ELEMENT_TYPES:
        try:
            for element in model.by_type(ifc_type):
                if element.id() in seen_ids:
                    continue
                seen_ids.add(element.id())

                psets = extract_psets(element)
                quantities = extract_quantities(element)
                materials = extract_materials(element)

                elements.append({
                    "element_id": element.id(),
                    "global_id": getattr(element, "GlobalId", ""),
                    "ifc_class": element.is_a(),
                    "type_name": _get_type_name(element),
                    "storey": element_to_storey.get(element.id(), "Nicht zugeordnet"),
                    "material": materials[0] if materials else "Unbekannt",
                    "materials_all": materials,
                    "psets": psets,
                    "area_m2": quantities.get("area"),
                    "volume_m3": quantities.get("volume"),
                    "length_m": quantities.get("length"),
                    "weight_kg": quantities.get("weight"),
                })
        except Exception:
            continue

    return elements


def extract_spaces(model, element_to_storey: dict) -> list[dict]:
    spaces = []
    try:
        for space in model.by_type("IfcSpace"):
            psets = extract_psets(space)
            quantities = extract_quantities(space)

            area = quantities.get("area")
            if area is None:
                area = _get_pset_value(psets, ["Pset_SpaceCommon", "BaseQuantities"], "NetFloorArea")

            volume = quantities.get("volume")
            height = None
            if area and volume and area > 0:
                height = volume / area

            usage = (
                getattr(space, "LongName", None)
                or _get_pset_value(psets, ["Pset_SpaceCommon"], "OccupancyType")
                or "Unbekannt"
            )

            spaces.append({
                "space_id": space.id(),
                "name": getattr(space, "Name", None) or f"Raum {space.id()}",
                "long_name": getattr(space, "LongName", None) or getattr(space, "Name", None) or f"Raum {space.id()}",
                "storey": element_to_storey.get(space.id(), "Nicht zugeordnet"),
                "usage": usage if usage else "Unbekannt",
                "area_m2": area,
                "volume_m3": volume,
                "height_m": height,
                "psets": psets,
            })
    except Exception:
        pass
    return spaces


def extract_storeys(model) -> list[dict]:
    storeys = []
    try:
        for storey in model.by_type("IfcBuildingStorey"):
            storeys.append({
                "name": storey.Name or f"Geschoss {storey.id()}",
                "elevation": getattr(storey, "Elevation", 0) or 0,
            })
        storeys.sort(key=lambda s: s["elevation"])
    except Exception:
        pass
    return storeys


def extract_psets(element) -> dict:
    psets = {}
    try:
        for definition in element.IsDefinedBy:
            if definition.is_a("IfcRelDefinesByProperties"):
                prop_set = definition.RelatingPropertyDefinition
                if prop_set.is_a("IfcPropertySet"):
                    pset_data = {}
                    for prop in prop_set.HasProperties:
                        if prop.is_a("IfcPropertySingleValue"):
                            try:
                                val = prop.NominalValue.wrappedValue if prop.NominalValue else None
                            except Exception:
                                val = None
                            pset_data[prop.Name] = val
                    psets[prop_set.Name] = pset_data
    except Exception:
        pass
    return psets


def extract_quantities(element) -> dict:
    quantities = {}
    try:
        for rel in element.IsDefinedBy:
            if rel.is_a("IfcRelDefinesByProperties"):
                qset = rel.RelatingPropertyDefinition
                if qset.is_a("IfcElementQuantity"):
                    for q in qset.Quantities:
                        try:
                            if q.is_a("IfcQuantityArea") and "area" not in quantities:
                                quantities["area"] = q.AreaValue
                            elif q.is_a("IfcQuantityVolume") and "volume" not in quantities:
                                quantities["volume"] = q.VolumeValue
                            elif q.is_a("IfcQuantityLength") and "length" not in quantities:
                                quantities["length"] = q.LengthValue
                            elif q.is_a("IfcQuantityWeight") and "weight" not in quantities:
                                quantities["weight"] = q.WeightValue
                        except Exception:
                            continue
    except Exception:
        pass
    return quantities


def extract_materials(element) -> list[str]:
    materials = []
    try:
        for rel in element.HasAssociations:
            if rel.is_a("IfcRelAssociatesMaterial"):
                mat = rel.RelatingMaterial
                if mat.is_a("IfcMaterial"):
                    if mat.Name:
                        materials.append(mat.Name)
                elif mat.is_a("IfcMaterialLayerSetUsage"):
                    for layer in mat.ForLayerSet.MaterialLayers:
                        if layer.Material and layer.Material.Name:
                            materials.append(layer.Material.Name)
                elif mat.is_a("IfcMaterialLayerSet"):
                    for layer in mat.MaterialLayers:
                        if layer.Material and layer.Material.Name:
                            materials.append(layer.Material.Name)
                elif mat.is_a("IfcMaterialList"):
                    for m in mat.Materials:
                        if m and m.Name:
                            materials.append(m.Name)
                elif mat.is_a("IfcMaterialConstituentSet"):
                    for constituent in mat.MaterialConstituents:
                        if constituent.Material and constituent.Material.Name:
                            materials.append(constituent.Material.Name)
    except Exception:
        pass
    return materials if materials else ["Unbekannt"]


def get_model_metadata(model) -> dict:
    metadata = {
        "project_name": "Unbekannt",
        "author": "Unbekannt",
        "organization": "Unbekannt",
        "schema": model.schema,
        "application": "Unbekannt",
        "element_count": 0,
        "space_count": 0,
        "storey_count": 0,
    }
    try:
        projects = model.by_type("IfcProject")
        if projects:
            p = projects[0]
            metadata["project_name"] = p.Name or "Unbekannt"

        persons = model.by_type("IfcPerson")
        if persons:
            p = persons[0]
            parts = [p.GivenName or "", p.FamilyName or ""]
            name = " ".join(x for x in parts if x).strip()
            metadata["author"] = name or "Unbekannt"

        orgs = model.by_type("IfcOrganization")
        if orgs:
            metadata["organization"] = orgs[0].Name or "Unbekannt"

        apps = model.by_type("IfcApplication")
        if apps:
            metadata["application"] = apps[0].ApplicationFullName or "Unbekannt"

        metadata["element_count"] = len(model.by_type("IfcBuildingElement"))
        metadata["space_count"] = len(model.by_type("IfcSpace"))
        metadata["storey_count"] = len(model.by_type("IfcBuildingStorey"))
    except Exception:
        pass
    return metadata


def _get_type_name(element) -> str:
    try:
        if element.ObjectType:
            return element.ObjectType
        if hasattr(element, "IsTypedBy") and element.IsTypedBy:
            rel = element.IsTypedBy[0]
            if rel.RelatingType and rel.RelatingType.Name:
                return rel.RelatingType.Name
    except Exception:
        pass
    return "Unbekannt"


def _get_pset_value(psets: dict, pset_names: list, prop_name: str):
    for pset_name in pset_names:
        pset = psets.get(pset_name, {})
        if prop_name in pset:
            return pset[prop_name]
    return None
