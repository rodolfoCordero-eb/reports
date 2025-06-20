import xml.etree.ElementTree as ET
import uuid
import os
from .draw_strategy import DrawStrategy
class drawio_draw(DrawStrategy):
    def name(self):
        return self.__class__.__name__
    
    def draw(self, elements, path, region):
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, f"{region}.drawio")

        def mx_cell(id, parent, value, style="shape=ellipse"):
            return ET.Element("mxCell", {
                "id": id,
                "value": value,
                "style": style,
                "vertex": "1",
                "parent": parent
            })

        def mx_geometry():
            geo = ET.Element("mxGeometry", {"x": "0", "y": "0", "width": "120", "height": "60"})
            geo.set("as", "geometry")
            return geo

        def add_node(parent, label, style):
            node_id = str(uuid.uuid4())[:8]
            cell = mx_cell(node_id, "1", label, style)
            cell.append(mx_geometry())
            parent.append(cell)
            return node_id

        # XML básico
        mxfile = ET.Element("mxfile")
        diagram = ET.SubElement(mxfile, "diagram", name=region)
        root = ET.Element("mxGraphModel")
        root.append(ET.Element("root"))

        # root contiene nodos visuales
        root_elt = root.find("root")
        root_elt.append(ET.Element("mxCell", id="0"))
        root_elt.append(ET.Element("mxCell", id="1", parent="0"))

        # Crear VPC como contenedor lógico (no se visualiza como cluster en drawio)
        vpc = elements.get("vpcs", [{}])[0]
        vpc_name = next((tag["Value"] for tag in vpc.get("Tags", []) if tag["Key"] == "Name"), vpc.get("VpcId", "VPC"))
        vpc_id = add_node(root_elt, vpc_name, "shape=swimlane")

        # Subnets e instancias
        for subnet in elements.get("subnets", []):
            subnet_name = next((tag["Value"] for tag in subnet.get("Tags", []) if tag["Key"] == "Name"), subnet["SubnetId"])
            subnet_id = add_node(root_elt, subnet_name, "shape=rectangle;fillColor=#e3f2fd")

            for instance in elements.get("instances", []):
                if instance.get("SubnetId") == subnet["SubnetId"]:
                    inst_id = add_node(root_elt, instance["InstanceId"], "shape=ellipse;fillColor=#ffffff")
                    # Conexión
                    edge = ET.Element("mxCell", {
                        "id": str(uuid.uuid4())[:8],
                        "style": "endArrow=block",
                        "edge": "1",
                        "source": subnet_id,
                        "target": inst_id,
                        "parent": "1"
                    })
                    edge.append(mx_geometry())
                    root_elt.append(edge)

        # Guardar archivo drawio
        diagram.append(root)
        tree = ET.ElementTree(mxfile)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)