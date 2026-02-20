from src.core.database import GlossaryTerm, Project, db
import csv
import json
import xml.etree.ElementTree as ET

class GlossaryManager:
    def __init__(self, project: Project = None):
        self.project = project

    def set_project(self, project: Project):
        self.project = project

    def add_term(self, source, target, category="general", notes=None, priority=10, case_sensitive=True, variants=None):
        if not self.project:
            return None
            
        try:
            return GlossaryTerm.create(
                project=self.project,
                source_term=source,
                target_term=target,
                category=category,
                notes=notes,
                priority=priority,
                case_sensitive=case_sensitive,
                variants=json.dumps(variants) if variants else None
            )
        except Exception:
            # Handle duplicates or DB errors
            return None

    def search(self, query):
        if not self.project:
            return []
            
        return GlossaryTerm.select().where(
            (GlossaryTerm.project == self.project) &
            (GlossaryTerm.source_term.contains(query))
        ).order_by(GlossaryTerm.priority.desc())

    def find_matches(self, text):
        """Find all glossary terms appearing in the text."""
        if not self.project or not text:
            return []
            
        terms = self.get_all()
        matches = []
        
        for term in terms:
            candidates = [term.source_term]
            if term.variants:
                try:
                    candidates.extend(json.loads(term.variants))
                except (json.JSONDecodeError, ValueError):
                    pass  # Invalid JSON in variants, skip
            
            for cand in candidates:
                if not cand: continue
                
                found = False
                if term.case_sensitive:
                    if cand in text:
                        found = True
                else:
                    if cand.lower() in text.lower():
                        found = True
                        
                if found:
                    matches.append(term)
                    break
        
        matches.sort(key=lambda x: (x.priority, len(x.source_term)), reverse=True)
        return matches

    def get_all(self):
        if not self.project:
            return []
        return list(GlossaryTerm.select().where(GlossaryTerm.project == self.project).order_by(GlossaryTerm.priority.desc()))

    def delete_term(self, term_id):
        GlossaryTerm.delete_by_id(term_id)

    def import_csv(self, file_path):
        if not self.project:
            return 0
            
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            with db.atomic():
                for row in reader:
                    if len(row) >= 2:
                        source = row[0]
                        target = row[1]
                        category = row[2] if len(row) > 2 else "general"
                        notes = row[3] if len(row) > 3 else None
                        try:
                            priority = int(row[4]) if len(row) > 4 else 10
                        except (ValueError, TypeError):
                            priority = 10  # Default priority on parse error
                        
                        self.add_term(source, target, category, notes, priority)
                        count += 1
        return count

    def export_tbx(self, output_path):
        """Export glossary to TBX format (OmegaT compatible)."""
        if not self.project:
            return 0
            
        terms = self.get_all()
        
        tbx_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        tbx_content += '<!DOCTYPE martif SYSTEM "TBX-BasicVersion2.dtd">\n'
        tbx_content += '<martif type="TBX-Basic" xml:lang="en">\n'
        tbx_content += '  <martifHeader>\n'
        tbx_content += '    <fileDesc>\n'
        tbx_content += '      <titleStmt>\n'
        tbx_content += f'        <title>Glossary - {self.project.name}</title>\n'
        tbx_content += '      </titleStmt>\n'
        tbx_content += '    </fileDesc>\n'
        tbx_content += '  </martifHeader>\n'
        tbx_content += '  <text>\n'
        tbx_content += '    <body>\n'
        
        for term in terms:
            tbx_content += '      <termEntry id="' + str(term.id) + '">\n'
            tbx_content += '        <descrip type="subjectField">' + self._escape_xml(term.category) + '</descrip>\n'
            tbx_content += '        <langSet xml:lang="source">\n'
            tbx_content += '          <tig>\n'
            tbx_content += '            <term>' + self._escape_xml(term.source_term) + '</term>\n'
            tbx_content += '          </tig>\n'
            tbx_content += '        </langSet>\n'
            tbx_content += '        <langSet xml:lang="target">\n'
            tbx_content += '          <tig>\n'
            tbx_content += '            <term>' + self._escape_xml(term.target_term) + '</term>\n'
            tbx_content += '          </tig>\n'
            tbx_content += '        </langSet>\n'
            tbx_content += '      </termEntry>\n'
        
        tbx_content += '    </body>\n'
        tbx_content += '  </text>\n'
        tbx_content += '</martif>'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tbx_content)
            
        return len(terms)

    def import_tbx(self, file_path):
        """Import glossary from TBX format."""
        if not self.project:
            return 0
            
        count = 0
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for term_entry in root.findall('.//termEntry'):
                source_term = ""
                target_term = ""
                category = "general"
                
                for lang_set in term_entry.findall('langSet'):
                    lang = lang_set.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_set.get('xml:lang', '')
                    tig = lang_set.find('tig')
                    if tig is not None:
                        term_elem = tig.find('term')
                        if term_elem is not None and term_elem.text:
                            if 'source' in lang.lower():
                                source_term = term_elem.text
                            else:
                                target_term = term_elem.text
                
                descrip = term_entry.find('.//descrip')
                if descrip is not None and descrip.text:
                    category = descrip.text
                
                if source_term and target_term:
                    self.add_term(source_term, target_term, category)
                    count += 1
                    
        except Exception as e:
            print(f"TBX Import Error: {e}")
            
        return count

    def _escape_xml(self, text):
        """Escape XML special characters."""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
