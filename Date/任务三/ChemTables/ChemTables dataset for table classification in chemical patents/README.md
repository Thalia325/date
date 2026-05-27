### JSON format of ChemTables Datasets

Here is an example of how a table is represented in *ChemTables* dataset. (The XML version uses XML string instead of 3-d list in the *'data'* field)
```JSON
{
  'annotations': 'PHARM',
  'data': [[['TABLE', '9'], [], [], []],
          [['TABLE', '9'], [], [], []],
          [[], [], [], []],
          [['Proteinurea', 'at', '25', 'Weeks', 'of', 'Age'], [], [], []],
          [[], [], ['%', 'Mice', 'with'], []],
          [[], ['Group'], ['Proteinurea', '>', '100', 'mg', '/', 'dL'], []],
          [[], [], [], []],
          [[], ['Vehicle'], ['54'], []],
          [[], ['Example', '2'], ['25'], []],
          [[], ['(', '0.05', 'mg', '/', 'kg', ';', '2x', 'week', ')'], [], []],
          [[], ['Example', '2'], ['17'], []],
          [[], ['(', '0.4', 'mg', '/', 'kg', ';', '2x', 'week', ')'], [], []],
          [[], ['Example', '2'], ['10'], []],
          [[], ['(', '2', 'mg', '/', 'kg', ';', '2x', 'week', ')'], [], []],
          [[], [], [], []]],
 'guid': 0,
 'pid': 'US20150315128A1',
 'tid': 'TABLE 9',
 'tuid': 'table-us-00012-en'
}
```

Usage of each field

| Field | Data Type | Description |
| --- | ----------- | -|
| annotations | *str* | Ground truth class label of the table |
| data | *list(list(list(str)))* | Content of the table, tokenized by OSCAR4 tokenizer |
| guid | *int* | Unique ID of the table in this dataset, can be used for tracking in error analysis|
| pid | *str* | ID of the patent where the table is extracted from |
| tid | *str* | Caption of the table |
| tuid | *str* | Unique identifier of the table in the original XML format patent|
