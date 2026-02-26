"""
TMX 1.4b handler for NovelTrad OmegaT-compliant projects.
Supports custom properties for project metadata and automatic segment insertion.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import os


class TMXHandler:
    """TMX 1.4b handler with custom NovelTrad properties."""
    
    TMX_VERSION = "1.4b"
    XMLNS = {
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'noveltrad': 'http://noveltrad.org/schema/v3',
    }
    
    CUSTOM_PROPERTIES = {
        'schema_version': 'x-noveltrad:schema_version',
        'genre': 'x-noveltrad:genre',
        'last_modified': 'x-noveltrad:last_modified',
        'project_name': 'x-noveltrad:project_name',
        'source_lang': 'x-noveltrad:source_lang',
        'target_lang': 'x-noveltrad:target_lang',
        'segmentation': 'x-noveltrad:segmentation',
    }
    
    def __init__(self, source_lang: str = 'en', target_lang: str = 'fr'):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.custom_props: Dict[str, str] = {}
    
    def create_header(self, root: ET.Element, custom_properties: Dict[str, Any] = None) -> ET.Element:
        """
        Create TMX header with custom properties.
        
        Args:
            root: TMX root element
            custom_properties: Custom metadata properties
            
        Returns:
            Header element
        """
        header_props = {
            'creationtool': 'NovelTrad',
            'creationtoolversion': '3.0.0',
            'datatype': 'PlainText',
            'segtype': 'sentence',
            'adminlang': 'en',
            'o-tmf': 'NovelTradDB',
            'srclang': self.source_lang,
        }
        
        if custom_properties:
            header_props.update(custom_properties)
        
        header = ET.SubElement(root, 'header', header_props)
        
        prop_map = {
            'schema_version': self.custom_props.get('schema_version', '3.0.0'),
            'genre': self.custom_props.get('genre', 'general'),
            'last_modified': self.custom_props.get('last_modified', datetime.utcnow().isoformat()),
            'project_name': self.custom_props.get('project_name', 'Unknown'),
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
        }
        
        for prop_name, prop_value in prop_map.items():
            if prop_value:
                self._add_property(header, prop_name, prop_value)
        
        return header
    
    def _add_property(self, parent: ET.Element, name: str, value: str) -> None:
        """Add a custom property element."""
        props = {
            'x-noveltrad:schema_version': '3.0.0',
            'x-noveltrad:genre': 'general',
            'x-noveltrad:last_modified': datetime.utcnow().isoformat(),
            'x-noveltrad:project_name': 'Unknown',
            'x-noveltrad:source_lang': self.source_lang,
            'x-noveltrad:target_lang': self.target_lang,
        }
        
        if name in props:
            props[name] = value
        
        prop_attrs = {
            '{http://www.w3.org/XML/1998/namespace}lang': 'x-noveltrad',
            'regid': props[name],
        }
        
        prop_elem = ET.SubElement(parent, 'prop', prop_attrs)
        prop_elem.text = props[name]
    
    def export_tmx(
        self,
        segments: List[Dict[str, Any]],
        output_path: str,
        custom_properties: Dict[str, Any] = None
    ) -> bool:
        """
        Export segments to TMX 1.4b format.
        
        Args:
            segments: List of {source_text, target_text} dicts
            output_path: Output TMX file path
            custom_properties: Additional custom properties
            
        Returns:
            Success status
        """
        try:
            root = ET.Element('tmx', version=self.TMX_VERSION)
            
            if custom_properties:
                self.custom_props.update(custom_properties)
            
            self._add_property(root, 'schema_version', self.custom_props.get('schema_version', '3.0.0'))
            self._add_property(root, 'genre', self.custom_props.get('genre', 'general'))
            self._add_property(root, 'last_modified', self.custom_props.get('last_modified', datetime.utcnow().isoformat()))
            
            body = ET.SubElement(root, 'body')
            
            for seg in segments:
                source_text = seg.get('source_text', '')
                target_text = seg.get('target_text', '')
                
                if not source_text or not target_text:
                    continue
                
                tu = ET.SubElement(body, 'tu')
                
                tuv_src = ET.SubElement(tu, 'tuv', {
                    '{http://www.w3.org/XML/1998/namespace}lang': self.source_lang
                })
                seg_src = ET.SubElement(tuv_src, 'seg')
                seg_src.text = source_text
                
                tuv_tgt = ET.SubElement(tu, 'tuv', {
                    '{http://www.w3.org/XML/1998/namespace}lang': self.target_lang
                })
                seg_tgt = ET.SubElement(tuv_tgt, 'seg')
                seg_tgt.text = target_text
            
            tree = ET.ElementTree(root)
            
            if hasattr(ET, 'indent'):
                ET.indent(tree, space='  ', level=0)
            
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            return True
            
        except Exception as e:
            print(f"TMX Export Error: {e}")
            return False
    
    def import_tmx(self, file_path: str) -> List[Tuple[str, str]]:
        """
        Import TMX file and return segment pairs.
        
        Args:
            file_path: Input TMX file path
            
        Returns:
            List of (source_text, target_text) tuples
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            pairs = []
            for tu in root.findall('.//tu'):
                tuvs = tu.findall('tuv')
                if len(tuvs) >= 2:
                    src_text = tuvs[0].find('seg').text or ''
                    tgt_text = tuvs[1].find('seg').text or ''
                    if src_text and tgt_text:
                        pairs.append((src_text, tgt_text))
            return pairs
            
        except Exception as e:
            print(f"TMX Import Error: {e}")
            return []
    
    def insert_or_update_segment(
        self,
        tmx_path: str,
        source_text: str,
        target_text: str,
        create_if_missing: bool = True
    ) -> bool:
        """
        Insert or update a segment in TMX file.
        
        Args:
            tmx_path: TMX file path
            source_text: Source text
            target_text: Target text
            create_if_missing: Create file if doesn't exist
            
        Returns:
            Success status
        """
        try:
            if not os.path.exists(tmx_path):
                if create_if_missing:
                    root = ET.Element('tmx', version=self.TMX_VERSION)
                    self.create_header(root)
                    body = ET.SubElement(root, 'body')
                    tree = ET.ElementTree(root)
                    if hasattr(ET, 'indent'):
                        ET.indent(tree, space='  ', level=0)
                    tree.write(tmx_path, encoding='utf-8', xml_declaration=True)
                else:
                    return False
            
            tree = ET.parse(tmx_path)
            root = tree.getroot()
            body = root.find('body')
            
            if body is None:
                body = ET.SubElement(root, 'body')
            
            for tu in body.findall('tu'):
                tuvs = tu.findall('tuv')
                if len(tuvs) >= 2:
                    existing_src = tuvs[0].find('seg').text or ''
                    if existing_src == source_text:
                        tuvs[1].find('seg').text = target_text
                        tree.write(tmx_path, encoding='utf-8', xml_declaration=True)
                        return True
            
            tu = ET.SubElement(body, 'tu')
            
            tuv_src = ET.SubElement(tu, 'tuv', {
                '{http://www.w3.org/XML/1998/namespace}lang': self.source_lang
            })
            seg_src = ET.SubElement(tuv_src, 'seg')
            seg_src.text = source_text
            
            tuv_tgt = ET.SubElement(tu, 'tuv', {
                '{http://www.w3.org/XML/1998/namespace}lang': self.target_lang
            })
            seg_tgt = ET.SubElement(tuv_tgt, 'seg')
            seg_tgt.text = target_text
            
            tree.write(tmx_path, encoding='utf-8', xml_declaration=True)
            return True
            
        except Exception as e:
            print(f"TMX Insert/Update Error: {e}")
            return False
    
    def get_custom_property(self, tmx_path: str, property_name: str) -> Optional[str]:
        """Get custom property value from TMX header."""
        try:
            tree = ET.parse(tmx_path)
            root = tree.getroot()
            
            header = root.find('header')
            if header is None:
                return None
            
            for prop in header.findall('prop'):
                regid = prop.get('regid', '')
                if regid == f'x-noveltrad:{property_name}':
                    return prop.text
            
            return None
            
        except Exception:
            return None
    
    def set_custom_property(self, tmx_path: str, property_name: str, value: str) -> bool:
        """Set custom property in TMX header."""
        try:
            tree = ET.parse(tmx_path)
            root = tree.getroot()
            
            header = root.find('header')
            if header is None:
                return False
            
            prop_found = False
            for prop in header.findall('prop'):
                regid = prop.get('regid', '')
                if regid == f'x-noveltrad:{property_name}':
                    prop.text = value
                    prop_found = True
                    break
            
            if not prop_found:
                prop = ET.SubElement(header, 'prop', {
                    '{http://www.w3.org/XML/1998/namespace}lang': 'x-noveltrad',
                    'regid': f'x-noveltrad:{property_name}'
                })
                prop.text = value
            
            tree.write(tmx_path, encoding='utf-8', xml_declaration=True)
            return True
            
        except Exception as e:
            print(f"Set Custom Property Error: {e}")
            return False
    
    def create_backup(self, tmx_path: str) -> str:
        """Create immediate backup of TMX file."""
        backup_path = f"{tmx_path}.bak"
        if os.path.exists(tmx_path):
            import shutil
            shutil.copy2(tmx_path, backup_path)
        return backup_path
    
    def create_timestamped_backup(self, tmx_path: str) -> str:
        """Create timestamped backup of TMX file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(tmx_path)[0]
        backup_path = f"{base_name}.timestamp.bak"
        if os.path.exists(tmx_path):
            import shutil
            shutil.copy2(tmx_path, backup_path)
        return backup_path
