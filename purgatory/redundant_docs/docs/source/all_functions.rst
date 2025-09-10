Complete Function Reference
===========================

Siege Utilities contains 521 auto-discovered functions.

siege_utilities.core.logging
----------------------------

.. autofunction:: siege_utilities.get_logger

.. autofunction:: siege_utilities.init_logger

.. autofunction:: siege_utilities.log_critical

.. autofunction:: siege_utilities.log_debug

.. autofunction:: siege_utilities.log_error

.. autofunction:: siege_utilities.log_info

.. autofunction:: siege_utilities.log_warning

.. autofunction:: siege_utilities.parse_log_level

siege_utilities.core.string_utils
---------------------------------

.. autofunction:: siege_utilities.remove_wrapping_quotes_and_trim

siege_utilities.distributed.hdfs_config
---------------------------------------

.. autofunction:: siege_utilities.create_cluster_config

.. autofunction:: siege_utilities.create_geocoding_config

.. autofunction:: siege_utilities.create_hdfs_config

.. autofunction:: siege_utilities.create_local_config

.. autofunction:: siege_utilities.dataclass

siege_utilities.distributed.hdfs_legacy
---------------------------------------

.. autofunction:: siege_utilities.check_hdfs_status

.. autofunction:: siege_utilities.get_quick_file_signature

siege_utilities.distributed.hdfs_operations
-------------------------------------------

.. autofunction:: siege_utilities.create_hdfs_operations

.. autofunction:: siege_utilities.setup_distributed_environment

siege_utilities.distributed.spark_utils
---------------------------------------

.. autofunction:: siege_utilities.abs

.. autofunction:: siege_utilities.acos

.. autofunction:: siege_utilities.acosh

.. autofunction:: siege_utilities.add_months

.. autofunction:: siege_utilities.aes_decrypt

.. autofunction:: siege_utilities.aes_encrypt

.. autofunction:: siege_utilities.aggregate

.. autofunction:: siege_utilities.any_value

.. autofunction:: siege_utilities.approx_count_distinct

.. autofunction:: siege_utilities.approx_percentile

.. autofunction:: siege_utilities.array

.. autofunction:: siege_utilities.array_agg

.. autofunction:: siege_utilities.array_append

.. autofunction:: siege_utilities.array_compact

.. autofunction:: siege_utilities.array_contains

.. autofunction:: siege_utilities.array_distinct

.. autofunction:: siege_utilities.array_except

.. autofunction:: siege_utilities.array_insert

.. autofunction:: siege_utilities.array_intersect

.. autofunction:: siege_utilities.array_join

.. autofunction:: siege_utilities.array_max

.. autofunction:: siege_utilities.array_min

.. autofunction:: siege_utilities.array_position

.. autofunction:: siege_utilities.array_prepend

.. autofunction:: siege_utilities.array_remove

.. autofunction:: siege_utilities.array_repeat

.. autofunction:: siege_utilities.array_size

.. autofunction:: siege_utilities.array_sort

.. autofunction:: siege_utilities.array_union

.. autofunction:: siege_utilities.arrays_overlap

.. autofunction:: siege_utilities.arrays_zip

.. autofunction:: siege_utilities.asc

.. autofunction:: siege_utilities.asc_nulls_first

.. autofunction:: siege_utilities.asc_nulls_last

.. autofunction:: siege_utilities.ascii

.. autofunction:: siege_utilities.asin

.. autofunction:: siege_utilities.asinh

.. autofunction:: siege_utilities.assert_true

.. autofunction:: siege_utilities.atan

.. autofunction:: siege_utilities.atan2

.. autofunction:: siege_utilities.atanh

.. autofunction:: siege_utilities.atomic_write_with_staging

.. autofunction:: siege_utilities.avg

.. autofunction:: siege_utilities.backup_full_dataframe

.. autofunction:: siege_utilities.base64

.. autofunction:: siege_utilities.bin

.. autofunction:: siege_utilities.bit_and

.. autofunction:: siege_utilities.bit_count

.. autofunction:: siege_utilities.bit_get

.. autofunction:: siege_utilities.bit_length

.. autofunction:: siege_utilities.bit_or

.. autofunction:: siege_utilities.bit_xor

.. autofunction:: siege_utilities.bitmap_bit_position

.. autofunction:: siege_utilities.bitmap_bucket_number

.. autofunction:: siege_utilities.bitmap_construct_agg

.. autofunction:: siege_utilities.bitmap_count

.. autofunction:: siege_utilities.bitmap_or_agg

.. autofunction:: siege_utilities.bitwise_not

.. autofunction:: siege_utilities.bool_and

.. autofunction:: siege_utilities.bool_or

.. autofunction:: siege_utilities.broadcast

.. autofunction:: siege_utilities.bround

.. autofunction:: siege_utilities.btrim

.. autofunction:: siege_utilities.bucket

.. autofunction:: siege_utilities.call_function

.. autofunction:: siege_utilities.call_udf

.. autofunction:: siege_utilities.cardinality

.. autofunction:: siege_utilities.cbrt

.. autofunction:: siege_utilities.ceil

.. autofunction:: siege_utilities.ceiling

.. autofunction:: siege_utilities.char

.. autofunction:: siege_utilities.char_length

.. autofunction:: siege_utilities.character_length

.. autofunction:: siege_utilities.clean_and_reorder_bbox

.. autofunction:: siege_utilities.coalesce

.. autofunction:: siege_utilities.col

.. autofunction:: siege_utilities.collate

.. autofunction:: siege_utilities.collation

.. autofunction:: siege_utilities.collect_list

.. autofunction:: siege_utilities.collect_set

.. autofunction:: siege_utilities.column

.. autofunction:: siege_utilities.compute_walkability

.. autofunction:: siege_utilities.concat

.. autofunction:: siege_utilities.concat_ws

.. autofunction:: siege_utilities.contains

.. autofunction:: siege_utilities.conv

.. autofunction:: siege_utilities.convert_timezone

.. autofunction:: siege_utilities.corr

.. autofunction:: siege_utilities.cos

.. autofunction:: siege_utilities.cosh

.. autofunction:: siege_utilities.cot

.. autofunction:: siege_utilities.count

.. autofunction:: siege_utilities.count_distinct

.. autofunction:: siege_utilities.count_if

.. autofunction:: siege_utilities.count_min_sketch

.. autofunction:: siege_utilities.covar_pop

.. autofunction:: siege_utilities.covar_samp

.. autofunction:: siege_utilities.crc32

.. autofunction:: siege_utilities.create_map

.. autofunction:: siege_utilities.create_unique_staging_directory

.. autofunction:: siege_utilities.csc

.. autofunction:: siege_utilities.cume_dist

.. autofunction:: siege_utilities.curdate

.. autofunction:: siege_utilities.current_catalog

.. autofunction:: siege_utilities.current_database

.. autofunction:: siege_utilities.current_date

.. autofunction:: siege_utilities.current_schema

.. autofunction:: siege_utilities.current_timestamp

.. autofunction:: siege_utilities.current_timezone

.. autofunction:: siege_utilities.current_user

.. autofunction:: siege_utilities.date_add

.. autofunction:: siege_utilities.date_diff

.. autofunction:: siege_utilities.date_format

.. autofunction:: siege_utilities.date_from_unix_date

.. autofunction:: siege_utilities.date_part

.. autofunction:: siege_utilities.date_sub

.. autofunction:: siege_utilities.date_trunc

.. autofunction:: siege_utilities.dateadd

.. autofunction:: siege_utilities.datediff

.. autofunction:: siege_utilities.datepart

.. autofunction:: siege_utilities.day

.. autofunction:: siege_utilities.dayname

.. autofunction:: siege_utilities.dayofmonth

.. autofunction:: siege_utilities.dayofweek

.. autofunction:: siege_utilities.dayofyear

.. autofunction:: siege_utilities.days

.. autofunction:: siege_utilities.decode

.. autofunction:: siege_utilities.degrees

.. autofunction:: siege_utilities.dense_rank

.. autofunction:: siege_utilities.desc

.. autofunction:: siege_utilities.desc_nulls_first

.. autofunction:: siege_utilities.desc_nulls_last

.. autofunction:: siege_utilities.e

.. autofunction:: siege_utilities.element_at

.. autofunction:: siege_utilities.elt

.. autofunction:: siege_utilities.encode

.. autofunction:: siege_utilities.endswith

.. autofunction:: siege_utilities.ensure_literal

.. autofunction:: siege_utilities.equal_null

.. autofunction:: siege_utilities.every

.. autofunction:: siege_utilities.exists

.. autofunction:: siege_utilities.exp

.. autofunction:: siege_utilities.explode

.. autofunction:: siege_utilities.explode_outer

.. autofunction:: siege_utilities.expm1

.. autofunction:: siege_utilities.export_prepared_df_as_csv_to_path_using_delimiter

.. autofunction:: siege_utilities.export_pyspark_df_to_excel

.. autofunction:: siege_utilities.expr

.. autofunction:: siege_utilities.extract

.. autofunction:: siege_utilities.factorial

.. autofunction:: siege_utilities.filter

.. autofunction:: siege_utilities.find_in_set

.. autofunction:: siege_utilities.first

.. autofunction:: siege_utilities.first_value

.. autofunction:: siege_utilities.flatten

.. autofunction:: siege_utilities.flatten_json_column_and_join_back_to_df

.. autofunction:: siege_utilities.floor

.. autofunction:: siege_utilities.forall

.. autofunction:: siege_utilities.format_number

.. autofunction:: siege_utilities.format_string

.. autofunction:: siege_utilities.from_csv

.. autofunction:: siege_utilities.from_json

.. autofunction:: siege_utilities.from_unixtime

.. autofunction:: siege_utilities.from_utc_timestamp

.. autofunction:: siege_utilities.from_xml

.. autofunction:: siege_utilities.get

.. autofunction:: siege_utilities.get_json_object

.. autofunction:: siege_utilities.get_row_count

.. autofunction:: siege_utilities.getbit

.. autofunction:: siege_utilities.greatest

.. autofunction:: siege_utilities.grouping

.. autofunction:: siege_utilities.grouping_id

.. autofunction:: siege_utilities.hash

.. autofunction:: siege_utilities.hex

.. autofunction:: siege_utilities.histogram_numeric

.. autofunction:: siege_utilities.hll_sketch_agg

.. autofunction:: siege_utilities.hll_sketch_estimate

.. autofunction:: siege_utilities.hll_union

.. autofunction:: siege_utilities.hll_union_agg

.. autofunction:: siege_utilities.hour

.. autofunction:: siege_utilities.hours

.. autofunction:: siege_utilities.hypot

.. autofunction:: siege_utilities.ifnull

.. autofunction:: siege_utilities.ilike

.. autofunction:: siege_utilities.initcap

.. autofunction:: siege_utilities.inline

.. autofunction:: siege_utilities.inline_outer

.. autofunction:: siege_utilities.input_file_block_length

.. autofunction:: siege_utilities.input_file_block_start

.. autofunction:: siege_utilities.input_file_name

.. autofunction:: siege_utilities.instr

.. autofunction:: siege_utilities.is_valid_utf8

.. autofunction:: siege_utilities.is_variant_null

.. autofunction:: siege_utilities.isnan

.. autofunction:: siege_utilities.isnotnull

.. autofunction:: siege_utilities.isnull

.. autofunction:: siege_utilities.java_method

.. autofunction:: siege_utilities.json_array_length

.. autofunction:: siege_utilities.json_object_keys

.. autofunction:: siege_utilities.json_tuple

.. autofunction:: siege_utilities.kurtosis

.. autofunction:: siege_utilities.lag

.. autofunction:: siege_utilities.last

.. autofunction:: siege_utilities.last_day

.. autofunction:: siege_utilities.last_value

.. autofunction:: siege_utilities.lcase

.. autofunction:: siege_utilities.lead

.. autofunction:: siege_utilities.least

.. autofunction:: siege_utilities.left

.. autofunction:: siege_utilities.length

.. autofunction:: siege_utilities.levenshtein

.. autofunction:: siege_utilities.like

.. autofunction:: siege_utilities.listagg

.. autofunction:: siege_utilities.listagg_distinct

.. autofunction:: siege_utilities.lit

.. autofunction:: siege_utilities.ln

.. autofunction:: siege_utilities.localtimestamp

.. autofunction:: siege_utilities.locate

.. autofunction:: siege_utilities.log

.. autofunction:: siege_utilities.log10

.. autofunction:: siege_utilities.log1p

.. autofunction:: siege_utilities.log2

.. autofunction:: siege_utilities.lower

.. autofunction:: siege_utilities.lpad

.. autofunction:: siege_utilities.ltrim

.. autofunction:: siege_utilities.make_date

.. autofunction:: siege_utilities.make_dt_interval

.. autofunction:: siege_utilities.make_interval

.. autofunction:: siege_utilities.make_timestamp

.. autofunction:: siege_utilities.make_timestamp_ltz

.. autofunction:: siege_utilities.make_timestamp_ntz

.. autofunction:: siege_utilities.make_valid_utf8

.. autofunction:: siege_utilities.make_ym_interval

.. autofunction:: siege_utilities.map_concat

.. autofunction:: siege_utilities.map_contains_key

.. autofunction:: siege_utilities.map_entries

.. autofunction:: siege_utilities.map_filter

.. autofunction:: siege_utilities.map_from_arrays

.. autofunction:: siege_utilities.map_from_entries

.. autofunction:: siege_utilities.map_keys

.. autofunction:: siege_utilities.map_values

.. autofunction:: siege_utilities.map_zip_with

.. autofunction:: siege_utilities.mark_valid_geocode_data

.. autofunction:: siege_utilities.mask

.. autofunction:: siege_utilities.max

.. autofunction:: siege_utilities.max_by

.. autofunction:: siege_utilities.md5

.. autofunction:: siege_utilities.mean

.. autofunction:: siege_utilities.median

.. autofunction:: siege_utilities.min

.. autofunction:: siege_utilities.min_by

.. autofunction:: siege_utilities.minute

.. autofunction:: siege_utilities.mode

.. autofunction:: siege_utilities.monotonically_increasing_id

.. autofunction:: siege_utilities.month

.. autofunction:: siege_utilities.monthname

.. autofunction:: siege_utilities.months

.. autofunction:: siege_utilities.months_between

.. autofunction:: siege_utilities.move_column_to_front_of_dataframe

.. autofunction:: siege_utilities.named_struct

.. autofunction:: siege_utilities.nanvl

.. autofunction:: siege_utilities.negate

.. autofunction:: siege_utilities.negative

.. autofunction:: siege_utilities.new_walkability_udf

.. autofunction:: siege_utilities.next_day

.. autofunction:: siege_utilities.now

.. autofunction:: siege_utilities.nth_value

.. autofunction:: siege_utilities.ntile

.. autofunction:: siege_utilities.nullif

.. autofunction:: siege_utilities.nullifzero

.. autofunction:: siege_utilities.nvl

.. autofunction:: siege_utilities.nvl2

.. autofunction:: siege_utilities.octet_length

.. autofunction:: siege_utilities.overlay

.. autofunction:: siege_utilities.pandas_udf

.. autofunction:: siege_utilities.parse_json

.. autofunction:: siege_utilities.parse_url

.. autofunction:: siege_utilities.percent_rank

.. autofunction:: siege_utilities.percentile

.. autofunction:: siege_utilities.percentile_approx

.. autofunction:: siege_utilities.pi

.. autofunction:: siege_utilities.pivot_summary_table_for_bools

.. autofunction:: siege_utilities.pivot_summary_with_metrics

.. autofunction:: siege_utilities.pmod

.. autofunction:: siege_utilities.posexplode

.. autofunction:: siege_utilities.posexplode_outer

.. autofunction:: siege_utilities.position

.. autofunction:: siege_utilities.positive

.. autofunction:: siege_utilities.pow

.. autofunction:: siege_utilities.power

.. autofunction:: siege_utilities.prepare_dataframe_for_export

.. autofunction:: siege_utilities.prepare_summary_dataframe

.. autofunction:: siege_utilities.print_debug_table

.. autofunction:: siege_utilities.printf

.. autofunction:: siege_utilities.product

.. autofunction:: siege_utilities.quarter

.. autofunction:: siege_utilities.radians

.. autofunction:: siege_utilities.raise_error

.. autofunction:: siege_utilities.rand

.. autofunction:: siege_utilities.randn

.. autofunction:: siege_utilities.randstr

.. autofunction:: siege_utilities.rank

.. autofunction:: siege_utilities.read_parquet_to_df

.. autofunction:: siege_utilities.reduce

.. autofunction:: siege_utilities.reflect

.. autofunction:: siege_utilities.regexp

.. autofunction:: siege_utilities.regexp_count

.. autofunction:: siege_utilities.regexp_extract

.. autofunction:: siege_utilities.regexp_extract_all

.. autofunction:: siege_utilities.regexp_instr

.. autofunction:: siege_utilities.regexp_like

.. autofunction:: siege_utilities.regexp_replace

.. autofunction:: siege_utilities.regexp_substr

.. autofunction:: siege_utilities.register_temp_table

.. autofunction:: siege_utilities.regr_avgx

.. autofunction:: siege_utilities.regr_avgy

.. autofunction:: siege_utilities.regr_count

.. autofunction:: siege_utilities.regr_intercept

.. autofunction:: siege_utilities.regr_r2

.. autofunction:: siege_utilities.regr_slope

.. autofunction:: siege_utilities.regr_sxx

.. autofunction:: siege_utilities.regr_sxy

.. autofunction:: siege_utilities.regr_syy

.. autofunction:: siege_utilities.repartition_and_cache

.. autofunction:: siege_utilities.repeat

.. autofunction:: siege_utilities.replace

.. autofunction:: siege_utilities.reproject_geom_columns

.. autofunction:: siege_utilities.reverse

.. autofunction:: siege_utilities.right

.. autofunction:: siege_utilities.rint

.. autofunction:: siege_utilities.rlike

.. autofunction:: siege_utilities.round

.. autofunction:: siege_utilities.row_number

.. autofunction:: siege_utilities.rpad

.. autofunction:: siege_utilities.rtrim

.. autofunction:: siege_utilities.sanitise_dataframe_column_names

.. autofunction:: siege_utilities.schema_of_csv

.. autofunction:: siege_utilities.schema_of_json

.. autofunction:: siege_utilities.schema_of_variant

.. autofunction:: siege_utilities.schema_of_variant_agg

.. autofunction:: siege_utilities.schema_of_xml

.. autofunction:: siege_utilities.sec

.. autofunction:: siege_utilities.second

.. autofunction:: siege_utilities.sentences

.. autofunction:: siege_utilities.sequence

.. autofunction:: siege_utilities.session_user

.. autofunction:: siege_utilities.session_window

.. autofunction:: siege_utilities.sha

.. autofunction:: siege_utilities.sha1

.. autofunction:: siege_utilities.sha2

.. autofunction:: siege_utilities.shiftleft

.. autofunction:: siege_utilities.shiftright

.. autofunction:: siege_utilities.shiftrightunsigned

.. autofunction:: siege_utilities.shuffle

.. autofunction:: siege_utilities.sign

.. autofunction:: siege_utilities.signum

.. autofunction:: siege_utilities.sin

.. autofunction:: siege_utilities.sinh

.. autofunction:: siege_utilities.size

.. autofunction:: siege_utilities.skewness

.. autofunction:: siege_utilities.slice

.. autofunction:: siege_utilities.some

.. autofunction:: siege_utilities.sort_array

.. autofunction:: siege_utilities.soundex

.. autofunction:: siege_utilities.spark_partition_id

.. autofunction:: siege_utilities.split

.. autofunction:: siege_utilities.split_part

.. autofunction:: siege_utilities.sqrt

.. autofunction:: siege_utilities.stack

.. autofunction:: siege_utilities.startswith

.. autofunction:: siege_utilities.std

.. autofunction:: siege_utilities.stddev

.. autofunction:: siege_utilities.stddev_pop

.. autofunction:: siege_utilities.stddev_samp

.. autofunction:: siege_utilities.str_to_map

.. autofunction:: siege_utilities.string_agg

.. autofunction:: siege_utilities.string_agg_distinct

.. autofunction:: siege_utilities.struct

.. autofunction:: siege_utilities.substr

.. autofunction:: siege_utilities.substring

.. autofunction:: siege_utilities.substring_index

.. autofunction:: siege_utilities.sum

.. autofunction:: siege_utilities.sum_distinct

.. autofunction:: siege_utilities.tabulate_null_vs_not_null

.. autofunction:: siege_utilities.tan

.. autofunction:: siege_utilities.tanh

.. autofunction:: siege_utilities.timestamp_add

.. autofunction:: siege_utilities.timestamp_diff

.. autofunction:: siege_utilities.timestamp_micros

.. autofunction:: siege_utilities.timestamp_millis

.. autofunction:: siege_utilities.timestamp_seconds

.. autofunction:: siege_utilities.to_binary

.. autofunction:: siege_utilities.to_char

.. autofunction:: siege_utilities.to_csv

.. autofunction:: siege_utilities.to_date

.. autofunction:: siege_utilities.to_json

.. autofunction:: siege_utilities.to_number

.. autofunction:: siege_utilities.to_timestamp

.. autofunction:: siege_utilities.to_timestamp_ltz

.. autofunction:: siege_utilities.to_timestamp_ntz

.. autofunction:: siege_utilities.to_unix_timestamp

.. autofunction:: siege_utilities.to_utc_timestamp

.. autofunction:: siege_utilities.to_varchar

.. autofunction:: siege_utilities.to_variant_object

.. autofunction:: siege_utilities.to_xml

.. autofunction:: siege_utilities.transform

.. autofunction:: siege_utilities.transform_keys

.. autofunction:: siege_utilities.transform_values

.. autofunction:: siege_utilities.translate

.. autofunction:: siege_utilities.trim

.. autofunction:: siege_utilities.trunc

.. autofunction:: siege_utilities.try_add

.. autofunction:: siege_utilities.try_aes_decrypt

.. autofunction:: siege_utilities.try_avg

.. autofunction:: siege_utilities.try_divide

.. autofunction:: siege_utilities.try_element_at

.. autofunction:: siege_utilities.try_make_interval

.. autofunction:: siege_utilities.try_make_timestamp

.. autofunction:: siege_utilities.try_make_timestamp_ltz

.. autofunction:: siege_utilities.try_make_timestamp_ntz

.. autofunction:: siege_utilities.try_mod

.. autofunction:: siege_utilities.try_multiply

.. autofunction:: siege_utilities.try_parse_json

.. autofunction:: siege_utilities.try_parse_url

.. autofunction:: siege_utilities.try_reflect

.. autofunction:: siege_utilities.try_subtract

.. autofunction:: siege_utilities.try_sum

.. autofunction:: siege_utilities.try_to_binary

.. autofunction:: siege_utilities.try_to_number

.. autofunction:: siege_utilities.try_to_timestamp

.. autofunction:: siege_utilities.try_url_decode

.. autofunction:: siege_utilities.try_validate_utf8

.. autofunction:: siege_utilities.try_variant_get

.. autofunction:: siege_utilities.typeof

.. autofunction:: siege_utilities.ucase

.. autofunction:: siege_utilities.udf

.. autofunction:: siege_utilities.udtf

.. autofunction:: siege_utilities.unbase64

.. autofunction:: siege_utilities.unhex

.. autofunction:: siege_utilities.uniform

.. autofunction:: siege_utilities.unix_date

.. autofunction:: siege_utilities.unix_micros

.. autofunction:: siege_utilities.unix_millis

.. autofunction:: siege_utilities.unix_seconds

.. autofunction:: siege_utilities.unix_timestamp

.. autofunction:: siege_utilities.unwrap_udt

.. autofunction:: siege_utilities.upper

.. autofunction:: siege_utilities.url_decode

.. autofunction:: siege_utilities.url_encode

.. autofunction:: siege_utilities.user

.. autofunction:: siege_utilities.validate_geocode_data

.. autofunction:: siege_utilities.validate_geometry

.. autofunction:: siege_utilities.validate_utf8

.. autofunction:: siege_utilities.var_pop

.. autofunction:: siege_utilities.var_samp

.. autofunction:: siege_utilities.variance

.. autofunction:: siege_utilities.variant_get

.. autofunction:: siege_utilities.version

.. autofunction:: siege_utilities.weekday

.. autofunction:: siege_utilities.weekofyear

.. autofunction:: siege_utilities.when

.. autofunction:: siege_utilities.width_bucket

.. autofunction:: siege_utilities.window

.. autofunction:: siege_utilities.window_time

.. autofunction:: siege_utilities.write_df_to_parquet

.. autofunction:: siege_utilities.xpath

.. autofunction:: siege_utilities.xpath_boolean

.. autofunction:: siege_utilities.xpath_double

.. autofunction:: siege_utilities.xpath_float

.. autofunction:: siege_utilities.xpath_int

.. autofunction:: siege_utilities.xpath_long

.. autofunction:: siege_utilities.xpath_number

.. autofunction:: siege_utilities.xpath_short

.. autofunction:: siege_utilities.xpath_string

.. autofunction:: siege_utilities.xxhash64

.. autofunction:: siege_utilities.year

.. autofunction:: siege_utilities.years

.. autofunction:: siege_utilities.zeroifnull

.. autofunction:: siege_utilities.zip_with

siege_utilities.files.hashing
-----------------------------

.. autofunction:: siege_utilities.calculate_file_hash

.. autofunction:: siege_utilities.generate_sha256_hash_for_file

.. autofunction:: siege_utilities.get_file_hash

.. autofunction:: siege_utilities.test_hash_functions

.. autofunction:: siege_utilities.verify_file_integrity

siege_utilities.files.operations
--------------------------------

.. autofunction:: siege_utilities.check_for_file_type_in_directory

.. autofunction:: siege_utilities.check_if_file_exists_at_path

.. autofunction:: siege_utilities.count_duplicate_rows_in_file_using_awk

.. autofunction:: siege_utilities.count_empty_rows_in_file_pythonically

.. autofunction:: siege_utilities.count_empty_rows_in_file_using_awk

.. autofunction:: siege_utilities.count_total_rows_in_file_pythonically

.. autofunction:: siege_utilities.count_total_rows_in_file_using_sed

.. autofunction:: siege_utilities.delete_existing_file_and_replace_it_with_an_empty_file

.. autofunction:: siege_utilities.remove_empty_rows_in_file_using_sed

.. autofunction:: siege_utilities.rmtree

.. autofunction:: siege_utilities.write_data_to_a_new_empty_file

.. autofunction:: siege_utilities.write_data_to_an_existing_file

siege_utilities.files.paths
---------------------------

.. autofunction:: siege_utilities.ensure_path_exists

.. autofunction:: siege_utilities.unzip_file_to_its_own_directory

siege_utilities.files.remote
----------------------------

.. autofunction:: siege_utilities.download_file

.. autofunction:: siege_utilities.generate_local_path_from_url

siege_utilities.files.shell
---------------------------

.. autofunction:: siege_utilities.run_subprocess

siege_utilities.geo.geocoding
-----------------------------

.. autofunction:: siege_utilities.concatenate_addresses

.. autofunction:: siege_utilities.use_nominatim_geocoder

