"""
Performance Benchmark Module for NovelTrad.
Tracks and displays translation speed metrics per engine.
Conforms to §12.12 of the specification.
"""
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class BenchmarkResult:
    """Result of a translation benchmark."""
    engine_name: str
    segment_count: int
    total_time_seconds: float
    avg_time_per_segment: float
    words_translated: int
    timestamp: str
    model_name: Optional[str] = None
    device: Optional[str] = None


class PerformanceBenchmark:
    """
    Tracks and analyzes translation performance across different engines.
    Helps users choose the best engine for their needs.
    """
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    def benchmark_translation(self, engine, segments: List[str], 
                            src_lang: str, tgt_lang: str,
                            glossary: List[Dict] = None) -> BenchmarkResult:
        """
        Benchmark a translation engine.
        
        Args:
            engine: Translation engine instance
            segments: List of text segments to translate
            src_lang: Source language code
            tgt_lang: Target language code
            glossary: Optional glossary terms
            
        Returns:
            BenchmarkResult with metrics
        """
        engine_name = engine.get_name() if hasattr(engine, 'get_name') else engine.__class__.__name__
        
        # Get model info if available
        model_name = None
        device = None
        if hasattr(engine, 'model'):
            model_name = engine.model
        if hasattr(engine, 'device'):
            device = engine.device
        
        # Warm-up (translate first segment separately)
        if segments:
            try:
                engine.translate(segments[0], src_lang, tgt_lang, glossary)
            except:
                pass
        
        # Benchmark
        start_time = time.time()
        for segment in segments:
            try:
                engine.translate(segment, src_lang, tgt_lang, glossary)
            except Exception as e:
                print(f"Translation error: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate metrics
        segment_count = len(segments)
        avg_time = total_time / segment_count if segment_count > 0 else 0
        words_translated = sum(len(s.split()) for s in segments)
        
        result = BenchmarkResult(
            engine_name=engine_name,
            segment_count=segment_count,
            total_time_seconds=round(total_time, 2),
            avg_time_per_segment=round(avg_time, 3),
            words_translated=words_translated,
            timestamp=datetime.now().isoformat(),
            model_name=model_name,
            device=device
        )
        
        self.results.append(result)
        return result
    
    def get_results(self, engine_name: str = None) -> List[BenchmarkResult]:
        """Get benchmark results, optionally filtered by engine."""
        if engine_name:
            return [r for r in self.results if r.engine_name == engine_name]
        return self.results
    
    def get_best_engine(self, criteria: str = 'speed') -> Optional[str]:
        """
        Get the best performing engine.
        
        Args:
            criteria: 'speed' (fastest) or 'efficiency' (most words/time)
        """
        if not self.results:
            return None
        
        if criteria == 'speed':
            # Fastest average per segment
            return min(self.results, key=lambda r: r.avg_time_per_segment).engine_name
        elif criteria == 'efficiency':
            # Most words per second
            best = max(self.results, key=lambda r: r.words_translated / r.total_time_seconds)
            return best.engine_name
        
        return None
    
    def generate_report(self) -> str:
        """Generate a text report of all benchmarks."""
        if not self.results:
            return "No benchmark results yet."
        
        lines = [
            "=" * 60,
            "TRANSLATION PERFORMANCE BENCHMARK REPORT",
            "=" * 60,
            ""
        ]
        
        # Group by engine
        engines = {}
        for r in self.results:
            if r.engine_name not in engines:
                engines[r.engine_name] = []
            engines[r.engine_name].append(r)
        
        for engine_name, results in engines.items():
            lines.append(f"📊 {engine_name}")
            lines.append("-" * 40)
            
            # Get latest result
            latest = results[-1]
            
            lines.append(f"  Segments: {latest.segment_count}")
            lines.append(f"  Total time: {latest.total_time_seconds}s")
            lines.append(f"  Avg per segment: {latest.avg_time_per_segment}s")
            lines.append(f"  Words translated: {latest.words_translated}")
            
            if latest.model_name:
                lines.append(f"  Model: {latest.model_name}")
            if latest.device:
                lines.append(f"  Device: {latest.device}")
            
            lines.append("")
        
        # Best engine
        best_speed = self.get_best_engine('speed')
        best_efficiency = self.get_best_engine('efficiency')
        
        lines.append("🏆 BEST PERFORMERS")
        lines.append("-" * 40)
        lines.append(f"  Speed: {best_speed}")
        lines.append(f"  Efficiency: {best_efficiency}")
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class BenchmarkDialog:
    """
    Dialog for running and displaying benchmarks.
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self.benchmark = PerformanceBenchmark()
    
    def run_benchmark(self, engine, test_segments: List[str], 
                     src_lang: str, tgt_lang: str):
        """Run benchmark on given engine."""
        result = self.benchmark.benchmark_translation(
            engine, test_segments, src_lang, tgt_lang
        )
        
        return result


def create_default_test_segments() -> List[str]:
    """
    Create default test segments for benchmarking.
    Includes various lengths and complexity.
    """
    return [
        "He walked into the room.",
        "The cultivation chamber was filled with spiritual energy.",
        "In the ancient world of xianxia, cultivators sought to transcend mortality through meditation and spirit refinement.",
        "The sect leader announced that the young disciple had broken through to the Foundation Establishment realm after only three years of cultivation.",
        "Xiao Ming looked at the massive dragon hovering above the clouds, its scales glittering like precious gems, and knew that this would be the battle of his life.",
    ]
