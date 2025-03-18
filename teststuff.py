import saxonche as saxonlib

PROCESSOR = saxonlib.PySaxonProcessor()
xml = PROCESSOR.parse_xml(xml_file_name="tests/tei/lb_diff_ab.xml")
xp = PROCESSOR.new_xpath_processor()
xp.declare_namespace("", "http://www.tei-c.org/ns/1.0")
xp.set_context(xdm_item=xml)
for x in xp.evaluate("//expan[1]"):
    print(str(x))