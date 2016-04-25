function addClass(element,classname)
{
  if(element.className)
  {
      if(element.className.search(new RegExp("\\b"+classname+"\\b")) == -1)
      {
          element.className = element.className +" "+ classname; 
      }
  }
  else
  {
      element.className = classname; 
  }
}

function isA (element,classname)
{
  if(element.className)
  {
      var classnameList = element.className.split(' ');
      var string = classname.toUpperCase();
      for(var i=0; i<classnameList.length; i++)
      {
          if(classnameList[i].toUpperCase() == string)
          {
              return true;
          }
      }
  }
  return false;
}

function removeClass(element,classname)
{
  element.className = element.className.replace(new RegExp("\\b"+classname+"\\b"),"");
}

function hideAll(classname)
	{
	var textElements = document.querySelectorAll("."+classname);
	for(var i = 0; i < textElements.length; i++)
		{
		textElements[i].classList.add("invisible");
		}
	}

function getAllCheckedBoxes(name)
{
var checkboxes = document.getElementsByName(name)
var checked_list = []
for(var cbi in checkboxes)
	{
	var cb = checkboxes[cbi];
	if(cb.checked&&cb.value)
		{
		checked_list.push(cb.value)
		}
	}
return checked_list;
}

function toggleAllCheckBoxes(name)
{
var checkboxes = document.getElementsByName(name)
for(var cbi in checkboxes)
	{
	var cb = checkboxes[cbi];
	if(cb.checked)
		{cb.checked=false;}
	else
		{cb.checked=true;}
	}
}


function sendPOST(url, postData, callback)
{
	var request = new XMLHttpRequest();
	request.onreadystatechange = function()
		{
		if (request.readyState == 4)
			{
			if (request.status == 200)
				{
				if(callback) callback(request);
				}
			else
				{
				console.log(request.statusText);
				}
			}
		};
	request.open("POST", url, true);
	/*request.setRequestHeader('Content-Type', 'multipart/form-data');*/
	var data = new FormData();
	data.append('json', JSON.stringify(postData));
	request.send(data);
}
function sendCommandAllCheckedBoxes(domain, command, list_name, data, callback)
	{
	var list = getAllCheckedBoxes(list_name)
	if(!data)
		{
		data={}
		}
		
	data[list_name] = list;
	sendPOST('https://ticatestdev.appspot.com/'+domain+'/'+command+'', data, callback)
	}

function fillSelectDictionary(selectId, data)
	{
	var select = document.getElementById(selectId);
	for(var i in data)
		{
		options += "<option value="+i+">"+data[i]['en']+" ("+data[i]['ja']+")</option>";
		}
	category.innerHTML = options;
	}
function fillSelectList(selectId, data)
	{
	var select = document.getElementById(selectId);
	var options = "";
	for(var i in data)
		{
		options += "<option value="+data[i]+">"+data[i]+"</option>";
		}
	select.innerHTML = options;
	}
function selectIfPresent(elementName,selectVal)
	{
	var element = document.getElementById(elementName)
	if(element!=null)
		{
		element.value = selectVal
		}
	}

encodingList = [
                 "ascii",
                 "big5",
                 "big5hkscs",
                 "cp037",
                 "cp424",
                 "cp437",
                 "cp500",
                 "cp720",
                 "cp737",
                 "cp775",
                 "cp850",
                 "cp852",
                 "cp855",
                 "cp856",
                 "cp857",
                 "cp858",
                 "cp860",
                 "cp861",
                 "cp862",
                 "cp863",
                 "cp864",
                 "cp865",
                 "cp866",
                 "cp869",
                 "cp874",
                 "cp875",
                 "cp932",
                 "cp949",
                 "cp950",
                 "cp1006",
                 "cp1026",
                 "cp1140",
                 "cp1250",
                 "cp1251",
                 "cp1252",
                 "cp1253",
                 "cp1254",
                 "cp1255",
                 "cp1256",
                 "cp1257",
                 "cp1258",
                 "euc_jp",
                 "euc_jis_2004",
                 "euc_jisx0213",
                 "euc_kr",
                 "gb2312",
                 "gbk",
                 "gb18030",
                 "hz",
                 "iso2022_jp",
                 "iso2022_jp_1",
                 "iso2022_jp_2",
                 "iso2022_jp_2004",
                 "iso2022_jp_3",
                 "iso2022_jp_ext",
                 "iso2022_kr",
                 "latin_1",
                 "iso8859_2",
                 "iso8859_3",
                 "iso8859_4",
                 "iso8859_5",
                 "iso8859_6",
                 "iso8859_7",
                 "iso8859_8",
                 "iso8859_9",
                 "iso8859_10",
                 "iso8859_13",
                 "iso8859_14",
                 "iso8859_15",
                 "iso8859_16",
                 "johab",
                 "koi8_r",
                 "koi8_u",
                 "mac_cyrillic",
                 "mac_greek",
                 "mac_iceland",
                 "mac_latin2",
                 "mac_roman",
                 "mac_turkish",
                 "ptcp154",
                 "shift_jis",
                 "shift_jis_2004",
                 "shift_jisx0213",
                 "utf_32",
                 "utf_32_be",
                 "utf_32_le",
                 "utf_16",
                 "utf_16_be",
                 "utf_16_le",
                 "utf_7",
                 "utf_8",
                 "utf_8_sig"]

window.addEventListener('load', function ()
	{
	}, false);

/* * * *    Keywords:   * * * */
	/* * *        New:        * * */


/* * * *   Questions:   * * * */


/* * * *    Sources:    * * * */

function sendRequest(url,postData,async)
	{
	requesType = "GET"
	if(postData != null)
		{
		requesType = "POST"
		}
	
	var request = new XMLHttpRequest();
	request.open("GET", url, async);
	request.send(postData);
	request.onreadystatechange = function()
		{
		if (request.readyState == 4)
			{
			if (request.status == 200)
				{
				//success(request.responseText);
				}
			else if (failure)
				{
				//failure(request.status, request.statusText);
				}
			}
		};
	}
