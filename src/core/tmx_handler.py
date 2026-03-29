import xml.etree.ElementTree as ET
from datetime import datetime
import os

class TMXHandler:
    @staticmethod
    def export_tmx(segments, source_lang, target_lang, output_path):
        """
        Exports a list of segment objects (with source_text and target_text) to a TMX file.
        Maintains legacy compat.
        """
        return TMXHandler.export_tmx_v3(segments, source_lang, target_lang, output_path)

    @staticmethod
    def export_tmx_v3(segments, source_lang, target_lang, output_path, include_status=True, include_metadata=True, custom_props=None):
        """
        Exports to TMX 1.4b with custom NovelTrad properties.
        """
        tmx = ET.Element('tmx', version='1.4')
        header = ET.SubElement(tmx, 'header', {
            'creationtool': 'NovelTrad',
            'creationtoolversion': '1.1',
            'datatype': 'PlainText',
            'segtype': 'sentence',
            'adminlang': 'en',
            'srclang': source_lang,
            'o-tmf': 'NovelTradDB'
        })
        
        if custom_props:
            for k, v in custom_props.items():
                prop = ET.SubElement(header, 'prop', {'type': f'x-noveltrad:{k}'})
                prop.text = str(v)
        
        body = ET.SubElement(tmx, 'body')
        
        for seg in segments:
            if not seg.target_text:
                continue
                
            tu = ET.SubElement(body, 'tu')
            
            # Status property
            if include_status and hasattr(seg, 'status') and seg.status:
                prop = ET.SubElement(tu, 'prop', {'type': 'x-noveltrad:status'})
                prop.text = str(seg.status.value if hasattr(seg.status, 'value') else seg.status)
                
            # Tu timestamp
            if hasattr(seg, 'last_modified') and seg.last_modified:
                modification_date = seg.last_modified.strftime("%Y%m%dT%H%M%SZ")
                tu.set('changedate', modification_date)

            # Source
            tuv_src = ET.SubElement(tu, 'tuv', {'xml:lang': source_lang})
            seg_src = ET.SubElement(tuv_src, 'seg')
            seg_src.text = seg.source_text
            
            # Target
            tuv_tgt = ET.SubElement(tu, 'tuv', {'xml:lang': target_lang})
            seg_tgt = ET.SubElement(tuv_tgt, 'seg')
            seg_tgt.text = seg.target_text
            
        tree = ET.ElementTree(tmx)
        if hasattr(ET, 'indent'):
            ET.indent(tree, space="  ", level=0)
            
        tree.write(str(output_path), encoding='utf-8', xml_declaration=True)
        return True

    @staticmethod
    def create_empty_tmx_v3(output_path, source_lang, target_lang, schema_version="3.0.0"):
        """Creates an empty project TM."""
        custom_props = {
            'schema_version': schema_version,
            'project_path': os.path.dirname(os.path.abspath(output_path))
        }
        return TMXHandler.export_tmx_v3([], source_lang, target_lang, output_path, custom_props=custom_props)

    @staticmethod
    def import_tmx(file_path):
        """
        Parses a TMX file and returns a list of (source_text, target_text) tuples.
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            pairs = []
            for tu in root.findall('.//tu'):
                tuvs = tu.findall('tuv')
                if len(tuvs) >= 2:
                    src_text = tuvs[0].find('seg').text or ""
                    tgt_text = tuvs[1].find('seg').text or ""
                    if src_text and tgt_text:
                        pairs.append((src_text, tgt_text))
            return pairs
        except Exception as e:
            print(f"Error reading TMX: {e}")
            return []

    @staticmethod
    def import_tmx_v3(file_path, project, strategy="update_if_empty"):
        """
        Imports a TMX 1.4b file into the given project, handling custom properties.
        Strategy can be 'update_if_empty' or 'overwrite'.
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            count = 0
            for tu in root.findall('.//tu'):
                props = {}
                for prop in tu.findall('prop'):
                    if 'type' in prop.attrib:
                        props[prop.attrib['type']] = prop.text
                        
                tuvs = tu.findall('tuv')
                if len(tuvs) >= 2:
                    src_text = tuvs[0].find('seg').text or ""
                    tgt_text = tuvs[1].find('seg').text or ""
                    
                    if src_text and tgt_text:
                        # Map string status back to integer if needed
                        from src.core.segment_status import SegmentStatus
                        status_val = SegmentStatus.MACHINE.value
                        if 'x-noveltrad:status' in props:
                            try:
                                status_str = props['x-noveltrad:status']
                                status_val = SegmentStatus.from_string(status_str).value
                            except:
                                pass
                                
                        from src.core.database import Segment
                        matches = Segment.select().where(
                            (Segment.project == project) & 
                            (Segment.source_text == src_text)
                        )
                        for seg in matches:
                            if strategy == "update_if_empty" and not seg.target_text:
                                seg.target_text = tgt_text
                                seg.status = status_val
                                seg.save()
                                count += 1
                            elif strategy == "overwrite":
                                seg.target_text = tgt_text
                                seg.status = status_val
                                seg.save()
                                count += 1
            return count
        except Exception as e:
            print(f"Error importing TMX v3: {e}")
            return 0
