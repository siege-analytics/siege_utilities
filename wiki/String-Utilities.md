# String Utilities Recipe

## Overview
This recipe demonstrates how to perform efficient text processing, manipulation, validation, and analysis using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from small text to massive distributed datasets.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- Basic understanding of text processing

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy regex unidecode  # Core dependencies
```

## Multi-Engine String Processing

### 1. Engine-Agnostic String Manager

```python
from siege_utilities.core.string_utils import StringUtils
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineStringManager:
    """String manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", spark_config=None):
        self.default_engine = default_engine
        self.string_utils = StringUtils()
        self.logger = Logger("multi_engine_string_manager")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
    
    def get_optimal_engine(self, text_size_mb=None, operation_complexity="medium"):
        """Automatically select the best engine for string operations"""
        
        if text_size_mb is None:
            return "auto"
        
        # Engine selection logic based on text size and operation complexity
        if text_size_mb < 10 and operation_complexity == "simple":
            return "pandas"
        elif text_size_mb < 100 and operation_complexity == "medium":
            return "pandas"
        elif text_size_mb >= 100 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def clean_text(self, text_data, cleaning_rules, engine=None, **kwargs):
        """Clean text using specified or auto-detected engine"""
        
        # Estimate text size for engine selection
        text_size_mb = self._estimate_text_size(text_data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(text_size_mb, "medium")
        
        self.logger.info(f"Cleaning text with {engine} engine (estimated size: {text_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._clean_text_with_spark(text_data, cleaning_rules, **kwargs)
        else:
            return self._clean_text_with_pandas(text_data, cleaning_rules, **kwargs)
    
    def validate_text(self, text_data, validation_rules, engine=None, **kwargs):
        """Validate text using specified or auto-detected engine"""
        
        # Estimate text size for engine selection
        text_size_mb = self._estimate_text_size(text_data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(text_size_mb, "medium")
        
        self.logger.info(f"Validating text with {engine} engine (estimated size: {text_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._validate_text_with_spark(text_data, validation_rules, **kwargs)
        else:
            return self._validate_text_with_pandas(text_data, validation_rules, **kwargs)
    
    def analyze_text(self, text_data, analysis_config, engine=None, **kwargs):
        """Analyze text using specified or auto-detected engine"""
        
        # Estimate text size for engine selection
        text_size_mb = self._estimate_text_size(text_data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(text_size_mb, "complex")
        
        self.logger.info(f"Analyzing text with {engine} engine (estimated size: {text_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._analyze_text_with_spark(text_data, analysis_config, **kwargs)
        else:
            return self._analyze_text_with_pandas(text_data, analysis_config, **kwargs)
    
    def _clean_text_with_spark(self, text_data, cleaning_rules, **kwargs):
        """Clean text using Spark for large datasets"""
        
        from pyspark.sql.functions import udf, col
        from pyspark.sql.types import StringType
        
        # Convert cleaning rules to Spark UDFs
        cleaning_udfs = {}
        
        for rule_name, rule_config in cleaning_rules.items():
            rule_type = rule_config.get("type")
            
            if rule_type == "remove_special_chars":
                @udf(returnType=StringType())
                def remove_special_chars(text):
                    if text is None:
                        return None
                    return self.string_utils.remove_special_characters(text, rule_config.get("keep_chars", ""))
                cleaning_udfs[rule_name] = remove_special_chars
            
            elif rule_type == "normalize_whitespace":
                @udf(returnType=StringType())
                def normalize_whitespace(text):
                    if text is None:
                        return None
                    return self.string_utils.normalize_whitespace(text)
                cleaning_udfs[rule_name] = normalize_whitespace
            
            elif rule_type == "convert_case":
                case_type = rule_config.get("case", "lower")
                @udf(returnType=StringType())
                def convert_case(text):
                    if text is None:
                        return None
                    if case_type == "lower":
                        return text.lower()
                    elif case_type == "upper":
                        return text.upper()
                    elif case_type == "title":
                        return text.title()
                    return text
                cleaning_udfs[rule_name] = convert_case
        
        # Apply cleaning rules
        cleaned_data = text_data
        for column, udf_func in cleaning_udfs.items():
            if column in text_data.columns:
                cleaned_data = cleaned_data.withColumn(column, udf_func(col(column)))
        
        return cleaned_data
    
    def _clean_text_with_pandas(self, text_data, cleaning_rules, **kwargs):
        """Clean text using Pandas for smaller datasets"""
        
        cleaned_data = text_data.copy()
        
        for rule_name, rule_config in cleaning_rules.items():
            rule_type = rule_config.get("type")
            
            if rule_type == "remove_special_chars":
                for column in rule_config.get("columns", text_data.columns):
                    if column in cleaned_data.columns:
                        cleaned_data[column] = cleaned_data[column].apply(
                            lambda x: self.string_utils.remove_special_characters(x, rule_config.get("keep_chars", "")) if pd.notna(x) else x
                        )
            
            elif rule_type == "normalize_whitespace":
                for column in rule_config.get("columns", text_data.columns):
                    if column in cleaned_data.columns:
                        cleaned_data[column] = cleaned_data[column].apply(
                            lambda x: self.string_utils.normalize_whitespace(x) if pd.notna(x) else x
                        )
            
            elif rule_type == "convert_case":
                case_type = rule_config.get("case", "lower")
                for column in rule_config.get("columns", text_data.columns):
                    if column in cleaned_data.columns:
                        if case_type == "lower":
                            cleaned_data[column] = cleaned_data[column].str.lower()
                        elif case_type == "upper":
                            cleaned_data[column] = cleaned_data[column].str.upper()
                        elif case_type == "title":
                            cleaned_data[column] = cleaned_data[column].str.title()
        
        return cleaned_data
    
    def _validate_text_with_spark(self, text_data, validation_rules, **kwargs):
        """Validate text using Spark for large datasets"""
        
        from pyspark.sql.functions import udf, col, when, lit
        from pyspark.sql.types import BooleanType, StructType, StructField
        
        validation_results = {}
        
        for rule_name, rule_config in validation_rules.items():
            rule_type = rule_config.get("type")
            
            if rule_type == "regex_pattern":
                pattern = rule_config.get("pattern")
                @udf(returnType=BooleanType())
                def regex_validation(text):
                    if text is None:
                        return False
                    import re
                    return bool(re.match(pattern, text))
                
                # Apply validation to specified columns
                for column in rule_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        validation_results[f"{rule_name}_{column}"] = text_data.withColumn(
                            f"valid_{column}", regex_validation(col(column))
                        )
            
            elif rule_type == "length_check":
                min_length = rule_config.get("min_length", 0)
                max_length = rule_config.get("max_length", float('inf'))
                
                @udf(returnType=BooleanType())
                def length_validation(text):
                    if text is None:
                        return False
                    text_length = len(text)
                    return min_length <= text_length <= max_length
                
                # Apply validation to specified columns
                for column in rule_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        validation_results[f"{rule_name}_{column}"] = text_data.withColumn(
                            f"valid_{column}", length_validation(col(column))
                        )
            
            elif rule_type == "required_values":
                required_values = rule_config.get("required_values", [])
                
                @udf(returnType=BooleanType())
                def required_values_validation(text):
                    if text is None:
                        return False
                    return text in required_values
                
                # Apply validation to specified columns
                for column in rule_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        validation_results[f"{rule_name}_{column}"] = text_data.withColumn(
                            f"valid_{column}", required_values_validation(col(column))
                        )
        
        return validation_results
    
    def _validate_text_with_pandas(self, text_data, validation_rules, **kwargs):
        """Validate text using Pandas for smaller datasets"""
        
        validation_results = {}
        
        for rule_name, rule_config in validation_rules.items():
            rule_type = rule_config.get("type")
            
            if rule_type == "regex_pattern":
                pattern = rule_config.get("pattern")
                import re
                
                for column in rule_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        validation_results[f"{rule_name}_{column}"] = text_data[column].apply(
                            lambda x: bool(re.match(pattern, x)) if pd.notna(x) else False
                        )
            
            elif rule_type == "length_check":
                min_length = rule_config.get("min_length", 0)
                max_length = rule_config.get("max_length", float('inf'))
                
                for column in rule_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        validation_results[f"{rule_name}_{column}"] = text_data[column].apply(
                            lambda x: min_length <= len(x) <= max_length if pd.notna(x) else False
                        )
            
            elif rule_type == "required_values":
                required_values = rule_config.get("required_values", [])
                
                for column in rule_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        validation_results[f"{rule_name}_{column}"] = text_data[column].apply(
                            lambda x: x in required_values if pd.notna(x) else False
                        )
        
        return validation_results
    
    def _analyze_text_with_spark(self, text_data, analysis_config, **kwargs):
        """Analyze text using Spark for large datasets"""
        
        from pyspark.sql.functions import udf, col, length, regexp_replace
        from pyspark.sql.types import IntegerType, DoubleType
        
        analysis_results = {}
        
        for analysis_name, analysis_config in analysis_config.items():
            analysis_type = analysis_config.get("type")
            
            if analysis_type == "word_count":
                @udf(returnType=IntegerType())
                def count_words(text):
                    if text is None:
                        return 0
                    return len(text.split())
                
                for column in analysis_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        analysis_results[f"{analysis_name}_{column}"] = text_data.withColumn(
                            f"word_count_{column}", count_words(col(column))
                        )
            
            elif analysis_type == "character_count":
                for column in analysis_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        analysis_results[f"{analysis_name}_{column}"] = text_data.withColumn(
                            f"char_count_{column}", length(col(column))
                        )
            
            elif analysis_type == "sentiment_analysis":
                # Simple sentiment analysis (can be enhanced with ML models)
                @udf(returnType=DoubleType())
                def simple_sentiment(text):
                    if text is None:
                        return 0.0
                    
                    positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
                    negative_words = ["bad", "terrible", "awful", "horrible", "disgusting"]
                    
                    text_lower = text.lower()
                    positive_count = sum(1 for word in positive_words if word in text_lower)
                    negative_count = sum(1 for word in negative_words if word in text_lower)
                    
                    if positive_count == 0 and negative_count == 0:
                        return 0.0
                    
                    return (positive_count - negative_count) / (positive_count + negative_count)
                
                for column in analysis_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        analysis_results[f"{analysis_name}_{column}"] = text_data.withColumn(
                            f"sentiment_{column}", simple_sentiment(col(column))
                        )
        
        return analysis_results
    
    def _analyze_text_with_pandas(self, text_data, analysis_config, **kwargs):
        """Analyze text using Pandas for smaller datasets"""
        
        analysis_results = {}
        
        for analysis_name, analysis_config in analysis_config.items():
            analysis_type = analysis_config.get("type")
            
            if analysis_type == "word_count":
                for column in analysis_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        analysis_results[f"{analysis_name}_{column}"] = text_data[column].apply(
                            lambda x: len(x.split()) if pd.notna(x) else 0
                        )
            
            elif analysis_type == "character_count":
                for column in analysis_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        analysis_results[f"{analysis_name}_{column}"] = text_data[column].apply(
                            lambda x: len(x) if pd.notna(x) else 0
                        )
            
            elif analysis_type == "sentiment_analysis":
                # Simple sentiment analysis
                positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
                negative_words = ["bad", "terrible", "awful", "horrible", "disgusting"]
                
                def simple_sentiment(text):
                    if pd.isna(text):
                        return 0.0
                    
                    text_lower = text.lower()
                    positive_count = sum(1 for word in positive_words if word in text_lower)
                    negative_count = sum(1 for word in negative_words if word in text_lower)
                    
                    if positive_count == 0 and negative_count == 0:
                        return 0.0
                    
                    return (positive_count - negative_count) / (positive_count + negative_count)
                
                for column in analysis_config.get("columns", text_data.columns):
                    if column in text_data.columns:
                        analysis_results[f"{analysis_name}_{column}"] = text_data[column].apply(simple_sentiment)
        
        return analysis_results
    
    def _estimate_text_size(self, text_data):
        """Estimate text data size in MB"""
        
        if hasattr(text_data, 'toPandas'):  # Spark DataFrame
            # Sample data to estimate size
            sample = text_data.limit(1000).toPandas()
            sample_size_mb = sample.memory_usage(deep=True).sum() / (1024 * 1024)
            # Estimate total size based on sample
            total_rows = text_data.count()
            estimated_size_mb = (sample_size_mb / 1000) * total_rows
            return estimated_size_mb
        else:  # Pandas DataFrame
            return text_data.memory_usage(deep=True).sum() / (1024 * 1024)
```

### 2. Multi-Engine Batch Text Processing

```python
class MultiEngineBatchTextProcessor:
    """Process multiple text datasets with optimal engine selection"""
    
    def __init__(self, string_manager):
        self.string_manager = string_manager
        self.logger = Logger("batch_text_processor")
    
    def process_text_batch(self, text_sources, processing_config, output_dir="output", engine="auto"):
        """Process multiple text sources using optimal engines for each"""
        
        results = {}
        
        for source_name, text_source in text_sources.items():
            try:
                # Process individual text source with optimal engine
                result = self._process_single_text_source(text_source, processing_config, output_dir, engine)
                results[source_name] = result
                
            except Exception as e:
                self.logger.error(f"Error processing {source_name}: {str(e)}")
                results[source_name] = {"error": str(e), "status": "failed"}
        
        return results
    
    def _process_single_text_source(self, text_source, processing_config, output_dir, engine):
        """Process a single text source with optimal engine selection"""
        
        # Load text data
        if isinstance(text_source, str):
            # Load from file
            text_data = self.string_manager._load_text_data(text_source, engine)
        else:
            text_data = text_source
        
        # Apply text processing pipeline
        processed_data = self._apply_text_processing(text_data, processing_config, engine)
        
        # Generate output filename
        base_name = f"processed_text_{int(time.time())}"
        output_path = f"{output_dir}/{base_name}.parquet"
        
        # Save processed data
        self._save_text_data(processed_data, output_path, engine)
        
        return {
            "input_source": text_source,
            "output_file": output_path,
            "engine_used": engine,
            "record_count": self._get_record_count(processed_data, engine),
            "status": "success"
        }
    
    def _apply_text_processing(self, text_data, processing_config, engine):
        """Apply text processing operations using specified engine"""
        
        # Apply cleaning rules
        if "cleaning" in processing_config:
            text_data = self.string_manager.clean_text(text_data, processing_config["cleaning"], engine)
        
        # Apply validation rules
        if "validation" in processing_config:
            validation_results = self.string_manager.validate_text(text_data, processing_config["validation"], engine)
            # Add validation columns to data
            for col_name, validation_col in validation_results.items():
                if engine == "spark":
                    text_data = text_data.withColumn(f"valid_{col_name}", validation_col)
                else:
                    text_data[f"valid_{col_name}"] = validation_col
        
        # Apply analysis rules
        if "analysis" in processing_config:
            analysis_results = self.string_manager.analyze_text(text_data, processing_config["analysis"], engine)
            # Add analysis columns to data
            for col_name, analysis_col in analysis_results.items():
                if engine == "spark":
                    text_data = text_data.withColumn(f"analysis_{col_name}", analysis_col)
                else:
                    text_data[f"analysis_{col_name}"] = analysis_col
        
        return text_data
    
    def _load_text_data(self, file_path, engine):
        """Load text data from file using specified engine"""
        
        if engine == "spark" and self.string_manager.spark_available:
            return self.string_manager.spark_utils.read_file(file_path)
        else:
            import pandas as pd
            return pd.read_csv(file_path)  # Assuming CSV format for text data
    
    def _save_text_data(self, data, output_path, engine):
        """Save text data to file using specified engine"""
        
        if engine == "spark":
            data.write.parquet(output_path)
        else:
            data.to_parquet(output_path, index=False)
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
```

### 3. Multi-Engine Text Quality Monitoring

```python
class MultiEngineTextQualityMonitor:
    """Monitor text quality and performance using any engine"""
    
    def __init__(self, string_manager):
        self.string_manager = string_manager
        self.logger = Logger("text_quality_monitor")
        self.quality_metrics = {}
    
    def monitor_text_quality(self, text_data, quality_config, engine="auto"):
        """Monitor text quality metrics using specified engine"""
        
        # Estimate text size for engine selection
        text_size_mb = self.string_manager._estimate_text_size(text_data)
        engine = engine or self.string_manager.get_optimal_engine(text_size_mb, "medium")
        
        # Collect quality metrics
        quality_metrics = self._collect_quality_metrics(text_data, quality_config, engine)
        
        # Store metrics for historical tracking
        timestamp = time.time()
        self.quality_metrics[timestamp] = {
            "engine": engine,
            "text_size_mb": text_size_mb,
            "metrics": quality_metrics
        }
        
        return quality_metrics
    
    def _collect_quality_metrics(self, text_data, quality_config, engine):
        """Collect quality metrics using specified engine"""
        
        metrics = {}
        
        # Text length metrics
        if "length_analysis" in quality_config:
            metrics["length_analysis"] = self._analyze_text_lengths(text_data, quality_config["length_analysis"], engine)
        
        # Character distribution metrics
        if "character_analysis" in quality_config:
            metrics["character_analysis"] = self._analyze_character_distribution(text_data, quality_config["character_analysis"], engine)
        
        # Word frequency metrics
        if "word_frequency" in quality_config:
            metrics["word_frequency"] = self._analyze_word_frequency(text_data, quality_config["word_frequency"], engine)
        
        # Data completeness metrics
        if "completeness" in quality_config:
            metrics["completeness"] = self._analyze_data_completeness(text_data, quality_config["completeness"], engine)
        
        return metrics
    
    def _analyze_text_lengths(self, text_data, config, engine):
        """Analyze text length distribution"""
        
        columns = config.get("columns", text_data.columns)
        length_metrics = {}
        
        for column in columns:
            if column in text_data.columns:
                if engine == "spark":
                    # Use Spark for length analysis
                    length_stats = text_data.select(length(col(column))).summary("count", "min", "25%", "50%", "75%", "max")
                    length_metrics[column] = length_stats.toPandas().to_dict()
                else:
                    # Use Pandas for length analysis
                    lengths = text_data[column].str.len()
                    length_metrics[column] = {
                        "count": len(lengths),
                        "min": lengths.min(),
                        "25%": lengths.quantile(0.25),
                        "50%": lengths.quantile(0.50),
                        "75%": lengths.quantile(0.75),
                        "max": lengths.max()
                    }
        
        return length_metrics
    
    def _analyze_character_distribution(self, text_data, config, engine):
        """Analyze character distribution in text"""
        
        columns = config.get("columns", text_data.columns)
        char_metrics = {}
        
        for column in columns:
            if column in text_data.columns:
                if engine == "spark":
                    # Use Spark for character analysis
                    @udf(returnType=StringType())
                    def get_char_distribution(text):
                        if text is None:
                            return "{}"
                        from collections import Counter
                        char_counts = Counter(text)
                        return str(dict(char_counts))
                    
                    char_dist = text_data.select(get_char_distribution(col(column))).collect()
                    char_metrics[column] = eval(char_dist[0][0]) if char_dist else {}
                else:
                    # Use Pandas for character analysis
                    from collections import Counter
                    all_chars = "".join(text_data[column].dropna().astype(str))
                    char_counts = Counter(all_chars)
                    char_metrics[column] = dict(char_counts)
        
        return char_metrics
    
    def _analyze_word_frequency(self, text_data, config, engine):
        """Analyze word frequency in text"""
        
        columns = config.get("columns", text_data.columns)
        word_metrics = {}
        
        for column in columns:
            if column in text_data.columns:
                if engine == "spark":
                    # Use Spark for word frequency analysis
                    @udf(returnType=StringType())
                    def get_word_frequency(text):
                        if text is None:
                            return "{}"
                        from collections import Counter
                        words = text.lower().split()
                        word_counts = Counter(words)
                        return str(dict(word_counts))
                    
                    word_freq = text_data.select(get_word_frequency(col(column))).collect()
                    word_metrics[column] = eval(word_freq[0][0]) if word_freq else {}
                else:
                    # Use Pandas for word frequency analysis
                    from collections import Counter
                    all_words = []
                    for text in text_data[column].dropna():
                        all_words.extend(text.lower().split())
                    word_counts = Counter(all_words)
                    word_metrics[column] = dict(word_counts)
        
        return word_metrics
    
    def _analyze_data_completeness(self, text_data, config, engine):
        """Analyze data completeness and quality"""
        
        columns = config.get("columns", text_data.columns)
        completeness_metrics = {}
        
        for column in columns:
            if column in text_data.columns:
                if engine == "spark":
                    # Use Spark for completeness analysis
                    total_count = text_data.count()
                    null_count = text_data.filter(col(column).isNull()).count()
                    empty_count = text_data.filter(col(column) == "").count()
                    
                    completeness_metrics[column] = {
                        "total_count": total_count,
                        "null_count": null_count,
                        "empty_count": empty_count,
                        "null_percentage": (null_count / total_count) * 100,
                        "empty_percentage": (empty_count / total_count) * 100,
                        "completeness_percentage": ((total_count - null_count - empty_count) / total_count) * 100
                    }
                else:
                    # Use Pandas for completeness analysis
                    total_count = len(text_data)
                    null_count = text_data[column].isnull().sum()
                    empty_count = (text_data[column] == "").sum()
                    
                    completeness_metrics[column] = {
                        "total_count": total_count,
                        "null_count": null_count,
                        "empty_count": empty_count,
                        "null_percentage": (null_count / total_count) * 100,
                        "empty_percentage": (empty_count / total_count) * 100,
                        "completeness_percentage": ((total_count - null_count - empty_count) / total_count) * 100
                    }
        
        return completeness_metrics
    
    def get_quality_trends(self, time_window_hours=24):
        """Get quality trends over time"""
        
        current_time = time.time()
        cutoff_time = current_time - (time_window_hours * 3600)
        
        # Filter metrics within time window
        recent_metrics = {
            timestamp: metrics for timestamp, metrics in self.quality_metrics.items()
            if timestamp >= cutoff_time
        }
        
        if not recent_metrics:
            return {}
        
        # Calculate trends
        trends = {}
        for metric_name in recent_metrics[list(recent_metrics.keys())[0]]["metrics"].keys():
            metric_values = []
            timestamps = []
            
            for timestamp, metrics in recent_metrics.items():
                if metric_name in metrics["metrics"]:
                    # Extract a summary value for the metric
                    summary_value = self._extract_summary_value(metrics["metrics"][metric_name])
                    metric_values.append(summary_value)
                    timestamps.append(timestamp)
            
            if len(metric_values) > 1:
                # Calculate trend (simple linear regression)
                trend_slope = self._calculate_trend_slope(timestamps, metric_values)
                trends[metric_name] = {
                    "trend_slope": trend_slope,
                    "trend_direction": "increasing" if trend_slope > 0 else "decreasing" if trend_slope < 0 else "stable",
                    "data_points": len(metric_values)
                }
        
        return trends
    
    def _extract_summary_value(self, metric_data):
        """Extract a summary value from metric data for trend analysis"""
        
        if isinstance(metric_data, dict):
            # Try to find a numeric value
            for key, value in metric_data.items():
                if isinstance(value, (int, float)):
                    return value
            # If no numeric value found, return 0
            return 0
        elif isinstance(metric_data, (int, float)):
            return metric_data
        else:
            return 0
    
    def _calculate_trend_slope(self, timestamps, values):
        """Calculate trend slope using simple linear regression"""
        
        if len(timestamps) < 2:
            return 0
        
        # Normalize timestamps to hours from first timestamp
        first_timestamp = min(timestamps)
        normalized_timestamps = [(t - first_timestamp) / 3600 for t in timestamps]
        
        # Calculate slope using least squares
        n = len(normalized_timestamps)
        sum_x = sum(normalized_timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(normalized_timestamps, values))
        sum_x2 = sum(x * x for x in normalized_timestamps)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
```

## Integration Examples

### 1. Multi-Engine Text Processing Pipeline

```python
def create_multi_engine_text_pipeline():
    """Create a complete multi-engine text processing pipeline"""
    
    # Initialize string manager
    string_manager = MultiEngineStringManager(default_engine="auto")
    
    # Create processors
    batch_processor = MultiEngineBatchTextProcessor(string_manager)
    quality_monitor = MultiEngineTextQualityMonitor(string_manager)
    
    # Define text sources
    text_sources = {
        "customer_reviews": "data/reviews/customer_reviews.csv",
        "product_descriptions": "data/products/product_descriptions.csv",
        "support_tickets": "data/support/support_tickets.csv"
    }
    
    # Define processing configuration
    processing_config = {
        "cleaning": {
            "remove_special_chars": {
                "type": "remove_special_chars",
                "columns": ["text", "title"],
                "keep_chars": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
            },
            "normalize_whitespace": {
                "type": "normalize_whitespace",
                "columns": ["text", "title"]
            },
            "convert_case": {
                "type": "convert_case",
                "columns": ["title"],
                "case": "title"
            }
        },
        "validation": {
            "length_check": {
                "type": "length_check",
                "columns": ["text"],
                "min_length": 10,
                "max_length": 1000
            },
            "required_values": {
                "type": "required_values",
                "columns": ["category"],
                "required_values": ["positive", "negative", "neutral"]
            }
        },
        "analysis": {
            "word_count": {
                "type": "word_count",
                "columns": ["text"]
            },
            "sentiment_analysis": {
                "type": "sentiment_analysis",
                "columns": ["text"]
            }
        }
    }
    
    # Define quality monitoring configuration
    quality_config = {
        "length_analysis": {"columns": ["text", "title"]},
        "character_analysis": {"columns": ["text"]},
        "word_frequency": {"columns": ["text"]},
        "completeness": {"columns": ["text", "title", "category"]}
    }
    
    # Process text with optimal engine selection
    processing_results = batch_processor.process_text_batch(
        text_sources, processing_config, "output/processed_text"
    )
    
    # Monitor quality for each processed dataset
    quality_results = {}
    for source_name, result in processing_results.items():
        if result.get("status") == "success":
            # Load processed data for quality monitoring
            processed_data = string_manager._load_text_data(result["output_file"], "auto")
            quality_results[source_name] = quality_monitor.monitor_text_quality(
                processed_data, quality_config
            )
    
    # Get quality trends
    quality_trends = quality_monitor.get_quality_trends(time_window_hours=24)
    
    return processing_results, quality_results, quality_trends

# Run the pipeline
text_pipeline_results = create_multi_engine_text_pipeline()
```

### 2. Real-time Text Quality Dashboard

```python
def create_text_quality_dashboard():
    """Create a dashboard to monitor text quality in real-time"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine Text Quality Dashboard"),
        
        html.Div([
            html.Div([
                html.Label("Quality Metric:"),
                dcc.Dropdown(
                    id="quality-metric",
                    options=[
                        {"label": "Text Length Distribution", "value": "length"},
                        {"label": "Character Distribution", "value": "character"},
                        {"label": "Word Frequency", "value": "word_freq"},
                        {"label": "Data Completeness", "value": "completeness"}
                    ],
                    value="length",
                    style={"width": "250px"}
                )
            ], style={"width": "300px", "margin": "20px"}),
            
            html.Div([
                html.Label("Time Window (hours):"),
                dcc.Slider(
                    id="time-window",
                    min=1,
                    max=72,
                    step=1,
                    value=24,
                    marks={i: str(i) for i in [1, 6, 12, 24, 48, 72]},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], style={"width": "400px", "margin": "20px"})
        ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}),
        
        html.Div([
            dcc.Graph(id="quality-chart"),
            dcc.Graph(id="trend-chart")
        ]),
        
        dcc.Interval(id="update-interval", interval=30000)  # Update every 30 seconds
    ])
    
    @app.callback(
        [Output("quality-chart", "figure"),
         Output("trend-chart", "figure")],
        [Input("update-interval", "n_intervals"),
         Input("quality-metric", "value"),
         Input("time-window", "value")]
    )
    def update_charts(n, metric, time_window):
        # Get quality data (this would come from your actual monitoring)
        # For demonstration, we'll create sample data
        
        if metric == "length":
            # Text length distribution chart
            categories = ["0-50", "51-100", "101-200", "201-500", "500+"]
            counts = [120, 450, 800, 600, 200]
            
            quality_fig = go.Figure(data=[
                go.Bar(x=categories, y=counts, name="Text Length Distribution")
            ])
            quality_fig.update_layout(title="Text Length Distribution", xaxis_title="Length Range", yaxis_title="Count")
            
        elif metric == "character":
            # Character distribution chart
            characters = ["a", "e", "i", "o", "u", "t", "n", "s", "r", "h"]
            frequencies = [8500, 7200, 6500, 5800, 5200, 4800, 4500, 4200, 3800, 3500]
            
            quality_fig = go.Figure(data=[
                go.Bar(x=characters, y=frequencies, name="Character Frequency")
            ])
            quality_fig.update_layout(title="Character Frequency Distribution", xaxis_title="Character", yaxis_title="Frequency")
        
        # Trend chart
        time_points = list(range(time_window))
        trend_values = [100 + i * 0.5 + np.random.normal(0, 2) for i in time_points]
        
        trend_fig = go.Figure(data=[
            go.Scatter(x=time_points, y=trend_values, mode="lines+markers", name="Quality Trend")
        ])
        trend_fig.update_layout(title=f"Quality Trend (Last {time_window} hours)", xaxis_title="Hours Ago", yaxis_title="Quality Score")
        
        return quality_fig, trend_fig
    
    return app

# Start the dashboard
text_quality_dashboard = create_text_quality_dashboard()
text_quality_dashboard.run_server(debug=True, port=8053)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for text < 10MB and simple operations
- Use **Spark** for text > 100MB and complex analysis
- Use **Auto-detection** for unknown text sizes and dynamic workloads
- Consider **text complexity** when selecting engine

### 2. Performance Optimization
- **Cache frequently processed text** in Spark
- **Use appropriate text formats** (CSV for small data, Parquet for large data)
- **Implement parallel processing** for multiple text sources
- **Monitor memory usage** and adjust engine selection accordingly

### 3. Text Quality
- **Validate text before processing** to catch issues early
- **Implement comprehensive error handling** for both engines
- **Use consistent validation rules** across all text types
- **Monitor text quality trends** over time

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Provide meaningful error messages** for debugging
- **Handle text encoding issues** gracefully
- **Retry failed operations** with different engines when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if string_manager.spark_available:
       print("Spark is available for large text processing")
   else:
       print("Using Pandas only")
   ```

2. **Memory Issues with Large Text**
   ```python
   # Use Spark for very large text
   if text_size_mb > 1000:
       engine = "spark"
   else:
       engine = "pandas"
   ```

3. **Text Encoding Issues**
   ```python
   # Handle encoding issues
   try:
       text_data = string_manager.clean_text(data, cleaning_rules, engine="pandas")
   except UnicodeDecodeError:
       # Try different encoding
       text_data = string_manager.clean_text(data, cleaning_rules, engine="pandas", encoding="latin-1")
   ```

## Conclusion

The multi-engine string utilities in `siege_utilities` provide:

- **Seamless scalability** from small text to massive datasets
- **Automatic engine selection** based on text characteristics
- **Unified interfaces** that work with both Spark and Pandas
- **Comprehensive text validation** and quality monitoring
- **Performance optimization** through intelligent engine selection

By following this recipe, you can build robust, scalable text processing pipelines that automatically adapt to your text sizes and processing requirements.
