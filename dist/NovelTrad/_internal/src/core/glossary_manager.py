from src.core.database import GlossaryTerm, Project, db
import csv

class GlossaryManager:
    def __init__(self, project: Project = None):
        self.project = project

    def set_project(self, project: Project):
        self.project = project

    def add_term(self, source, target, category="general"):
        if not self.project:
            return None
            
        try:
            return GlossaryTerm.create(
                project=self.project,
                source_term=source,
                target_term=target,
                category=category
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
        )

    def get_all(self):
        if not self.project:
            return []
        return list(GlossaryTerm.select().where(GlossaryTerm.project == self.project))

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
                        self.add_term(row[0], row[1], row[2] if len(row) > 2 else "general")
                        count += 1
        return count
