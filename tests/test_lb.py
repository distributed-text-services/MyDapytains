from dapitains.tei.document import Document



if __name__ == "__main__":
    doc = Document("./tei/epigraphy.xml")
    # print(doc.get_reffs())
    print(doc.get_passage("2"))