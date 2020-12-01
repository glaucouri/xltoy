### xltoy Rules

* During the data ingestion phase xltoy start collecting cells from known **working areas**.

* Working areas are *named ranges* set in **Name Manager**, they are of 3 types:
  - **data**: defines the area that delimits the data sources, it enable some features like diff positional or relative
  - **model**: define the model area, it must be one row or one column. 
  - **names**: if present it is used to give a mnemonic name to each equation in the model area. It must be coupled 
    to an omonimous model range.
  Type is distinguished by a regular expression defined in settings file. 
  By default string with suffix *data_* *model_* *names_* case insensitive. 
    
* Only one type for *working area* can be set for each sheet. The main idea here is to promote some kind of discipline 
  and order models one for sheet.
  
* Model must be a range of one column or row, optionally aligned with names range. Aligned means that ranges must start
  from same position and must have the same shape. With this technique, each names is coupled to his equation. If names
  range is not given equation will be named as sequence of anon_* names.    