filterStruct = [
  {
    "filter": "tags",
    "fieldType": "string",
    "description": "Comma separated tag list to filter by"
  },
  {
    "filter": "version",
    "fieldType": "string",
    "description": "Version to return"
  }

]


ontologies = {
  "d1": {
      "id": "duo",
      "terms": [
        {'id': 'DUO:0000018', 'shorthand': 'NPUNCU', 'name': 'not for profit, non commercial use only', 'definition': 'This data use modifier indicates that use of the data is limited to not-for-profit organizations and not-for-profit use, non-commercial use.'}, 
        {'id': 'DUO:0000012', 'shorthand': 'RS', 'name': 'research specific restrictions', 'definition': 'This data use modifier indicates that use is limited to studies of a certain research type.'}
      ]
  },
  "d2": {
    "id": "duo",
    "terms": [
      {'shorthand': 'RU',
       'name': 'research use only',
       'definition': 'This secondary category consent code indicates that use is limited to research purposes (e.g., does not include its use in clinical care).',
       'id': 'DUO:0000014'},

      {'shorthand': 'TS-[XX]',
       'name': 'time limit on use',
       'definition': 'This requirement indicates that use is approved for a specific number of months.',
       'id': 'DUO:0000025'}
    ]
  }
}
