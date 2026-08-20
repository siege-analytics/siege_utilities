# `parsons.Table` ↔ `pandas.DataFrame` round-trip matrix (P0-3)

Generated: 2026-08-20T03:41:22.591893+00:00

Parsons version: 6.1.0

pandas version: 3.0.5

Python version: 3.11.11


## Summary table

| Case | Description | Table→DF→Table | DF→Table→DF |
|---|---|:---:|:---:|
| `empty` | Empty table (0 rows, 0 cols) | ✅ PASS | ✅ PASS |
| `empty_headers` | Header-only table (0 rows, 2 cols) | ✅ PASS | ✅ PASS |
| `single_row` | Single-row table | ✅ PASS | ✅ PASS |
| `large_10k` | 10,000-row synthetic table | ✅ PASS | ✅ PASS |
| `mixed_types` | Mixed types (int/float/str/datetime/None/NaN/bool/list/dict) | ❌ FAIL | ✅ PASS |
| `weird_columns` | Column names: spaces, unicode, SQL reserved words | ✅ PASS | ✅ PASS |
| `duplicate_columns` | Duplicated column name (lossiness check) | ✅ PASS | ✅ PASS |
| `all_none_column` | Column entirely None (nullability check) | ✅ PASS | ✅ PASS |

## Per-case details

### `empty` — Empty table (0 rows, 0 cols)

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [],
    "roundtripped_records": [],
    "df_dtypes": {}
  },
  "df_to_table": {
    "df_before_dtypes": {},
    "df_after_dtypes": {}
  }
}
```

</details>


### `empty_headers` — Header-only table (0 rows, 2 cols)

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [],
    "roundtripped_records": [],
    "df_dtypes": {
      "col_a": "object",
      "col_b": "object"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "col_a": "object",
      "col_b": "object"
    },
    "df_after_dtypes": {
      "col_a": "object",
      "col_b": "object"
    }
  }
}
```

</details>


### `single_row` — Single-row table

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [
      {
        "name": "alpha",
        "count": 1
      }
    ],
    "roundtripped_records": [
      {
        "name": "alpha",
        "count": 1
      }
    ],
    "df_dtypes": {
      "name": "str",
      "count": "int64"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "name": "str",
      "count": "int64"
    },
    "df_after_dtypes": {
      "name": "str",
      "count": "int64"
    }
  }
}
```

</details>


### `large_10k` — 10,000-row synthetic table

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [
      {
        "id": 0,
        "value": 0
      },
      {
        "id": 1,
        "value": 2
      },
      {
        "id": 2,
        "value": 4
      },
      "... (9997 more elided; rerun spike for full)"
    ],
    "roundtripped_records": [
      {
        "id": 0,
        "value": 0
      },
      {
        "id": 1,
        "value": 2
      },
      {
        "id": 2,
        "value": 4
      },
      "... (9997 more elided; rerun spike for full)"
    ],
    "df_dtypes": {
      "id": "int64",
      "value": "int64"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "id": "int64",
      "value": "int64"
    },
    "df_after_dtypes": {
      "id": "int64",
      "value": "int64"
    }
  }
}
```

</details>


### `mixed_types` — Mixed types (int/float/str/datetime/None/NaN/bool/list/dict)

- **Table→DF→Table:** records differ after round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [
      {
        "i": 1,
        "f": 2.5,
        "s": "hello",
        "d": "2026-01-01 00:00:00+00:00",
        "none_col": null,
        "nan_col": NaN,
        "b": true,
        "lst": [
          1,
          2,
          3
        ],
        "dct": {
          "key": "value"
        }
      },
      {
        "i": 2,
        "f": 3.14,
        "s": "world",
        "d": "2026-06-15 00:00:00+00:00",
        "none_col": null,
        "nan_col": NaN,
        "b": false,
        "lst": [],
        "dct": {}
      }
    ],
    "roundtripped_records": [
      {
        "i": 1,
        "f": 2.5,
        "s": "hello",
        "d": "2026-01-01 00:00:00+00:00",
        "none_col": null,
        "nan_col": NaN,
        "b": true,
        "lst": [
          1,
          2,
          3
        ],
        "dct": {
          "key": "value"
        }
      },
      {
        "i": 2,
        "f": 3.14,
        "s": "world",
        "d": "2026-06-15 00:00:00+00:00",
        "none_col": null,
        "nan_col": NaN,
        "b": false,
        "lst": [],
        "dct": {}
      }
    ],
    "df_dtypes": {
      "i": "int64",
      "f": "float64",
      "s": "str",
      "d": "datetime64[us, UTC]",
      "none_col": "object",
      "nan_col": "float64",
      "b": "bool",
      "lst": "object",
      "dct": "object"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "i": "int64",
      "f": "float64",
      "s": "str",
      "d": "datetime64[us, UTC]",
      "none_col": "object",
      "nan_col": "float64",
      "b": "bool",
      "lst": "object",
      "dct": "object"
    },
    "df_after_dtypes": {
      "i": "int64",
      "f": "float64",
      "s": "str",
      "d": "datetime64[us, UTC]",
      "none_col": "object",
      "nan_col": "float64",
      "b": "bool",
      "lst": "object",
      "dct": "object"
    }
  }
}
```

</details>


### `weird_columns` — Column names: spaces, unicode, SQL reserved words

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [
      {
        "col with spaces": 1,
        "unicode_\u540d\u524d": "a",
        "select": "x",
        "from": "y",
        "where": "z"
      },
      {
        "col with spaces": 2,
        "unicode_\u540d\u524d": "b",
        "select": "x2",
        "from": "y2",
        "where": "z2"
      }
    ],
    "roundtripped_records": [
      {
        "col with spaces": 1,
        "unicode_\u540d\u524d": "a",
        "select": "x",
        "from": "y",
        "where": "z"
      },
      {
        "col with spaces": 2,
        "unicode_\u540d\u524d": "b",
        "select": "x2",
        "from": "y2",
        "where": "z2"
      }
    ],
    "df_dtypes": {
      "col with spaces": "int64",
      "unicode_\u540d\u524d": "str",
      "select": "str",
      "from": "str",
      "where": "str"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "col with spaces": "int64",
      "unicode_\u540d\u524d": "str",
      "select": "str",
      "from": "str",
      "where": "str"
    },
    "df_after_dtypes": {
      "col with spaces": "int64",
      "unicode_\u540d\u524d": "str",
      "select": "str",
      "from": "str",
      "where": "str"
    }
  }
}
```

</details>


### `duplicate_columns` — Duplicated column name (lossiness check)

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [
      {
        "col": 2
      },
      {
        "col": 4
      }
    ],
    "roundtripped_records": [
      {
        "col": 2
      },
      {
        "col": 4
      }
    ],
    "df_dtypes": {
      "col": "int64"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "col": "int64"
    },
    "df_after_dtypes": {
      "col": "int64"
    }
  }
}
```

</details>


### `all_none_column` — Column entirely None (nullability check)

- **Table→DF→Table:** clean round-trip
- **DF→Table→DF:** clean round-trip

<details><summary>Artifacts</summary>


```json
{
  "table_to_df": {
    "original_records": [
      {
        "id": 1,
        "always_none": null
      },
      {
        "id": 2,
        "always_none": null
      },
      {
        "id": 3,
        "always_none": null
      }
    ],
    "roundtripped_records": [
      {
        "id": 1,
        "always_none": null
      },
      {
        "id": 2,
        "always_none": null
      },
      {
        "id": 3,
        "always_none": null
      }
    ],
    "df_dtypes": {
      "id": "int64",
      "always_none": "object"
    }
  },
  "df_to_table": {
    "df_before_dtypes": {
      "id": "int64",
      "always_none": "object"
    },
    "df_after_dtypes": {
      "id": "int64",
      "always_none": "object"
    }
  }
}
```

</details>



## Overall

Total FAILs across both directions: **1**

At least one case fails. Every FAIL becomes a design finding in the adapter's guardrails. See per-case detail above.
