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

function fillCategory(categoryId, data)
	{
	var category = document.getElementById(categoryId);
	var options = "<option></optiom>";
	for(var i in data)
		{
		options += "<option value="+i+">"+data[i]['en']+" ("+data[i]['ja']+")</option>";
		}
	category.innerHTML = options;
	}
function fillSubCategory(subCategoryId, categoryId, data)
	{
	var subCategory = document.getElementById(subCategoryId);
	var category = document.getElementById(categoryId).value;
	subCategory.innerHTML = "";
	var options = "<option></optiom>";
	var categoryData = data[category];
	for(var i in categoryData)
		{
		options += "<option value="+i+">"+categoryData[i]+"</option>";
		}
	subCategory.innerHTML = options;
	}

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
