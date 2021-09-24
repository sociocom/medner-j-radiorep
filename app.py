import xml.etree.ElementTree as ET

import mojimoji
from textformatting import ssplit
from flask import Flask, Markup, render_template, request, session
from medner_j import Ner

model = Ner.from_pretrained(model_name="radiology", normalizer="dict")

# to html
TAGNAMES = {
    "d": "disease",
    "a": "anatomical",
    "f": "feature",
    "c": "change",
    "TIMEX3": "TIMEX3",
    "t-test": "testtest",
    "t-key": "testkey",
    "tval": "testval",
    "m-key": "medkey",
    "m-val": "medval",
    "cc": "cc",
    "r": "remedy",
    "p": "pending",
}

app = Flask(__name__)
app.secret_key = "0a1f4c96f1c6e4e32fdf25b6e8516f77"


def e_xml2html(entity):
    attrv = entity.attrib.values()
    if len(attrv) == 1:
        entity.attrib = {"class": f"{TAGNAMES[entity.tag]}-{list(attrv)[0]}"}
    elif len(attrv) == 0:
        entity.attrib = {"class": f"{TAGNAMES[entity.tag]}"}
    else:
        entity.attrib = {"class": f"{TAGNAMES[entity.tag]} {' '.join(attrv)}"}
    entity.tag = "span"


def xml2html(doc):
    if isinstance(doc, str):
        root = ET.fromstring(doc)
    else:
        root = doc
    for entity in root.iter():
        if entity.tag == "root":
            continue
        elif entity.tag == "br":
            continue
        e_xml2html(entity)
    return (
        ET.tostring(root, encoding="unicode", method="html")
        .replace("<root>", "")
        .replace("</root>", "")
    )


def mednerj2xml(analysed_text):
    at_br = analysed_text.replace("\n", "<br />")
    xmldoc = f"<root>{at_br}</root>"
    root = ET.fromstring(xmldoc)
    for entity in root.iter():
        if entity.tag == "root":
            continue
        if entity.tag == "br":
            continue

        if "value" in entity.attrib:
            del entity.attrib["value"]

        if entity.tag == "TIMEX3DATE":
            entity.tag = "TIMEX3"
            entity.attrib["type"] = "DATE"
        elif entity.tag == "TIMEX3CC":
            entity.tag = "TIMEX3"
            entity.attrib["type"] = "CC"
        elif entity.tag == "d":
            entity.tag = "d"
        elif entity.tag == "dpositive":
            entity.tag = "d"
            entity.attrib["certainty"] = "positive"
        elif entity.tag == "dnegative":
            entity.tag = "d"
            entity.attrib["certainty"] = "negative"
        elif entity.tag == "dsuspicious":
            entity.tag = "d"
            entity.attrib["certainty"] = "suspicious"
        elif entity.tag == "mkeyexecuted":
            entity.tag = "m-key"
            entity.attrib["state"] = "executed"
        elif entity.tag == "mvalexecuted":
            entity.tag = "m-val"
            entity.attrib["state"] = "executed"
        elif entity.tag == "rexecuted":
            entity.tag = "r"
            entity.attrib["state"] = "executed"
        elif entity.tag == "ttestexecuted":
            entity.tag = "t-test"
            entity.attrib["state"] = "executed"
        elif entity.tag == "ttestother":
            entity.tag = "t-test"
            entity.attrib["state"] = "other"
        elif entity.tag == "ccother":
            entity.tag = "cc"
            entity.attrib["state"] = "other"

    return root


def analyse(text):
    text = mojimoji.han_to_zen(text)
    # texts = text.split("\n")
    sentences = ssplit(text)
    analysed_text = model.predict(sentences)
    xml = mednerj2xml("\n".join(analysed_text))
    return xml


# form input
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        if "html" in session:
            session.pop("html", None)
        # return send_from_directory("static", "index.html")
        return render_template("index.html")
    else:
        input_rr = request.form.get("radiorep")
        if input_rr:
            analysed_xml = analyse(request.form["radiorep"].strip())
            radiorep_ner = Markup(xml2html(analysed_xml))
            session["html"] = radiorep_ner
            return render_template(
                "index.html",
                radiorep=input_rr,
                radiorep_ner=radiorep_ner,
            )
        else:
            return render_template("index.html")
        # return render_template("index.html", radiorep_ner=r"<span class=\"disease\">ERROR: 解析に失敗しました……</span>")


if __name__ == "__main__":
    app.run(debug=True)
