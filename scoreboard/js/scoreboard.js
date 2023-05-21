window.onload = init;

function init(){
	
	var xhr = new XMLHttpRequest(); //AJAX data request sent to server(in this case server being local json file)
	var streamJSON = '../../data/scoreboard.json'; //specifies path for streamcontrol output json
	var scObj; //variable to hold data extracted from parsed json
	var startup = true; //flag for if looping functions are on their first pass or not
	var animated = false; //flag for if scoreboard animation has run or not
	var cBust = 0; //variable to hold cache busting value
	var game; //variable to hold game value from streamcontrol dropdown
	var p1Wrap = $('#p1Wrapper'); //variables to shortcut copypasting text resize functions
	var p2Wrap = $('#p2Wrapper');
	var rdResize = $('#round');
	var p1Result = $('#results1');
	var p2Result = $('#results2');
	var next1 = $('#next1');
	var next2 = $('#next2');
	var gameHold;
	var countryHold1;
	var countryHold2;
	
	xhr.overrideMimeType('application/json'); //explicitly declares that json should always be processed as a json filetype
	
	function pollJSON() {
		xhr.open('GET',streamJSON+'?v='+cBust,true); //string query-style cache busting, forces non-cached new version of json to be opened each time
		//xhr.open('GET', "http://192.168.0.131:8080/getdata"); //Go to local server
		xhr.send();
		cBust++;		
	}
	
	pollJSON();
	setInterval(function(){pollJSON();},1000); //runs polling function twice per second
	
	xhr.onreadystatechange = parseJSON; //runs parseJSON function every time XMLHttpRequest ready state changes
	
	function parseJSON() {
		if(xhr.readyState === 4){ //loads data from json into scObj variable each time that XMLHttpRequest ready state reports back as '4'(successful)
			scObj = JSON.parse(xhr.responseText);
			if(animated == true){
				scoreboard(); //runs scoreboard function each time readyState reports back as 4 as long as it has already run once and changed animated value to false
			}
		}
	}
	
	function scoreboard(){
		
		if(startup == true){
			game = scObj['game'];
			gameHold = game; //sets 'game' value into placeholder div
			
			if(game == 'BBTAG' || game == 'SFVAE' || game == 'TEKKEN7' || game == 'UNIST'){
				$('#scoreboardVid').attr('src','../webm/scoreboard_1.webm');
			}
			else if(game == 'BBCF' || game == 'DBFZ' || game == 'GGXRD' || game == 'KOFXIV' || game == 'MVCI' || game == 'UMVC3' || game == 'ST'){
				$('#scoreboardVid').attr('src','../webm/scoreboard_2.webm'); //changes webm to 2nd one if appropriate game is picked
				TweenMax.set('#leftWrapper',{css:{y: adjust2}}); //sets scoreboard text wrappers to match placement of 2nd webm
				TweenMax.set('#rightWrapper',{css:{y: adjust2}});
			}
			else if(game == 'USF4'){
				$('#scoreboardVid').attr('src','../webm/scoreboard_3.webm');
				TweenMax.set('#leftWrapper',{css:{y: adjust3}});
				TweenMax.set('#rightWrapper',{css:{y: adjust3}});
			}
			else{				
				$('#scoreboardVid').attr('src','../webm/scoreboard_2.webm');
				TweenMax.set('#leftWrapper',{css:{y: adjust2}}); //if 'game' value is anything other than specified above it defaults to 2nd webm/placement
				TweenMax.set('#rightWrapper',{css:{y: adjust2}});
			}
			if(game == 'BBTAG' || game == 'UNIST'){
				var adjustLgW = parseFloat($('.logos').css('width')) * adjustLg[2]; //shrinks logo sizes based on scaling variable set in scoreboard.html
				var adjustLgH = parseFloat($('.logos').css('height')) * adjustLg[2];
				TweenMax.set('.logos',{css:{x: adjustLg[0], y: adjustLg[1], width: adjustLgW, height: adjustLgH}});
			}
			
			//document.getElementById('scoreboardVid').play(); //plays scoreboard video
			
			getData(); //runs function that sets data polled from json into html objects
			setTimeout(logoLoop,logoTime); //sets logoLoop function out in time specified in logoTime variable in scoreboard.html
			startup = false; //flags that the scoreboard/getData functions have run their first pass
			animated = true; //flags that the scoreboard video animation has run
		}
		else{
			getData(); //if startup is not set to true, only the getData function is run each time scoreboard function runs
		}
	}
	
	setTimeout(scoreboard,300);
	
	function getData(){
		
		var p1Name = scObj['p1Name']; //creates local variables to store data parsed from json
		var p2Name = scObj['p2Name'];
		var p1Team = scObj['p1Team'];
		var p2Team = scObj['p2Team'];
		var p1Score = scObj['p1Score'];
		var p2Score = scObj['p2Score'];
		var round = scObj['round'];
		var p1Country = scObj['p1Country'];
		var p2Country = scObj['p2Country'];
		var resultPlayer1 = scObj['resultplayer1'];
		var resultPlayer2 = scObj['resultplayer2'];
		var resultScore1 = scObj['resultscore1'];
        var resultScore2 = scObj['resultscore2'];
        var nextPlayer1 = scObj['nextplayer1'];
        var nextPlayer2 = scObj['nextplayer2'];
		
		if(startup == true){
			
			TweenMax.set('#p1Wrapper',{css:{x: p1Move}}); //sets name/round wrappers to starting positions for them to animate from
			TweenMax.set('#p2Wrapper',{css:{x: p2Move}});
			TweenMax.set('#round',{css:{y: rdMove}});
			
			$('#p1Name').html(p1Name); //changes html object values to values stored in local variables
			$('#p2Name').html(p2Name);
			$('#p1Team').html(p1Team);
			$('#p2Team').html(p2Team);
			$('#p1Score').html(p1Score);
			$('#p2Score').html(p2Score);
			$('#round').html(round);
			$('result1Name').html(resultPlayer1);
			$('result2Name').html(resultPlayer2);
			$('result1').html(resultScore1);
            $('result2').html(resultScore2);
            $('nextPlayer1').html(nextPlayer1);
            $('nextPlayer2').html(nextPlayer2);

			countryHold1 = p1Country;
			countryHold2 = p2Country;
			
			$("#p1Country").attr("src","../imgs/countries/"+countryFlag(p1Country)+".png").on("error",function(){
				$("#p1Country").attr("src","../imgs/countries/world.png");
			});
			
			$("#p2Country").attr("src","../imgs/countries/"+countryFlag(p2Country)+".png").on("error",function(){
				$("#p2Country").attr("src","../imgs/countries/world.png");
			});
						
			p1Wrap.each(function(i, p1Wrap){ //function to resize font if text string is too long and causes div to overflow its width/height boundaries
				while(p1Wrap.scrollWidth > p1Wrap.offsetWidth || p1Wrap.scrollHeight > p1Wrap.offsetHeight){
					var newFontSize = parseInt(parseFloat($("#p1Name").css('font-size').slice(0,-2)) * .95) + 'px';
					$("#p1Name").css('font-size', newFontSize);
					var newTeamFontSize = parseInt(parseFloat($("#p1Team").css('font-size').slice(0,-2)) * .95) + 'px';
					$("#p1Team").css('font-size', newTeamFontSize);
				}
			});
			
			p2Wrap.each(function(i, p2Wrap){
				while(p2Wrap.scrollWidth > p2Wrap.offsetWidth || p2Wrap.scrollHeight > p2Wrap.offsetHeight){
					var newFontSize = parseInt(parseFloat($("#p2Name").css('font-size').slice(0,-2)) * .95) + 'px';
					$("#p2Name").css('font-size', newFontSize);
					var newTeamFontSize = parseInt(parseFloat($("#p2Team").css('font-size').slice(0,-2)) * .95) + 'px';
					$("#p2Team").css('font-size', newTeamFontSize);
				}
				return true;
			});
			
			rdResize.each(function(i, rdResize){
				while(rdResize.scrollWidth > rdResize.offsetWidth || rdResize.scrollHeight > rdResize.offsetHeight){
					var newFontSize = (parseFloat($(rdResize).css('font-size').slice(0,-2)) * .95) + 'px';
					$(rdResize).css('font-size', newFontSize);
				}
				return true;
			});

			p1Result.each(function(i, p1Result){
                while(p1Result.scrollWidth > p1Result.offsetWidth || p1Result.scrollHeight > p1Result.offsetHeight){
                    var newFontSize = (parseFloat($('#result1Name').css('font-size').slice(0,-2)) * .95) + 'px';
                    $('#result1Name').css('font-size', newFontSize);
                }
				return true;
            });

			p2Result.each(function(i, p2Result){
                while(p2Result.scrollWidth > p2Result.offsetWidth || p2Result.scrollHeight > p2Result.offsetHeight){
                    var newFontSize = (parseFloat($('#result2Name').css('font-size').slice(0,-2)) * .95) + 'px';
                    $('#result2Name').css('font-size', newFontSize);
                }
				return true;
            });

            next1.each(function(i, next1){
                while(next1.scrollWidth > next1.offsetWidth || next1.scrollHeight > next1.offsetHeight){
                    var newFontSize = (parseFloat($('#nextPlayer1').css('font-size').slice(0,-2)) * .95) + 'px';
                    $('#nextPlayer1').css('font-size', newFontSize);
                }
				return true;
            });

            next2.each(function(i, next2){
                while(next2.scrollWidth > next2.offsetWidth || next2.scrollHeight > next2.offsetHeight){
                    var newFontSize = (parseFloat($('#nextPlayer2').css('font-size').slice(0,-2)) * .95) + 'px';
                    $('#nextPlayer2').css('font-size', newFontSize);
                }
				return true;
            });

			TweenMax.to('#p1Wrapper',nameTime,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:nameDelay}); //animates wrappers traveling back to default css positions while
			TweenMax.to('#p2Wrapper',nameTime,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:nameDelay}); //fading them in, timing/delay based on variables set in scoreboard.html
			TweenMax.to('#round',rdTime,{css:{opacity: 1},ease:Quad.easeOut,delay:rdDelay});
			TweenMax.to('.scores',scTime,{css:{opacity: 1},ease:Quad.easeOut,delay:scDelay});
			TweenMax.to("#p1Country",.4,{css:{opacity: 1},delay:.3});
			TweenMax.to("#p2Country",.4,{css:{opacity: 1},delay:.3});
			TweenMax.to('#results1',nameTime,{css:{opacity: 1},ease:Quad.easeOut,delay:nameDelay}); //fading them in, timing/delay based on variables set in scoreboard.html
			TweenMax.to('#results2',nameTime,{css:{opacity: 1},ease:Quad.easeOut,delay:nameDelay}); //fading them in, timing/delay based on variables set in scoreboard.html
			TweenMax.to('#next1',nameTime,{css:{opacity: 1},ease:Quad.easeOut,delay:nameDelay}); //fading them in, timing/delay based on variables set in scoreboard.html
            TweenMax.to('#next2',nameTime,{css:{opacity: 1},ease:Quad.easeOut,delay:nameDelay}); //fading them in, timing/delay based on variables set in scoreboard.html
			
// Disabling toggle between flag and team			
//			TweenMax.to("#p1Country",1,{css:{opacity: 0},delay:10,repeat:-1,repeatDelay:10,yoyo:true});
//			TweenMax.to("#p1TFlag",1,{css:{opacity: 1},delay:10,repeat:-1,repeatDelay:10,yoyo:true});
//			TweenMax.to("#p2Country",1,{css:{opacity: 0},delay:10,repeat:-1,repeatDelay:10,yoyo:true});
//			TweenMax.to("#p2TFlag",1,{css:{opacity: 1},delay:10,repeat:-1,repeatDelay:10,yoyo:true});
		}
		else{
			game = scObj['game']; //if this is after the first time that getData function has run, changes the value of the local game variable to current json output
			
			if($('#p1Name').text() != p1Name || $('#p1Team').text() != p1Team){ //if either name or team do not match, fades out wrapper and updates them both
				TweenMax.to('#p1Wrapper',.3,{css:{x: p1Move, opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){ //uses onComplete parameter to execute function after TweenMax
					$('#p1Name').css('font-size',nameSize).html(p1Name); //updates name and team html objects with current json values
					$('#p1Team').css('font-size', teamNameSize).html(p1Team);
			
					p1Wrap.each(function(i, p1Wrap){//same resize functions from above
						while(p1Wrap.scrollWidth > p1Wrap.offsetWidth || p1Wrap.scrollHeight > p1Wrap.offsetHeight){
							var newFontSize = parseInt(parseFloat($("#p1Name").css('font-size').slice(0,-2)) * .95) + 'px';
							$('#p1Name').css('font-size', newFontSize);
							var newTeamFontSize = parseInt(parseFloat($("#p1Team").css('font-size').slice(0,-2)) * .95) + 'px';
							$("#p1Team").css('font-size', newTeamFontSize);
						}
					});
					
					TweenMax.to('#p1Wrapper',.3,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:.2}); //fades name wrapper back in while moving to original position
				}});
			}
			
			if($('#p2Name').text() != p2Name || $('#p2Team').text() != p2Team){
				TweenMax.to('#p2Wrapper',.3,{css:{x: p2Move, opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
					$('#p2Name').css('font-size',nameSize).html(p2Name);
					$('#p2Team').css('font-size', teamNameSize).html(p2Team);
			
					p2Wrap.each(function(i, p2Wrap){
						while(p2Wrap.scrollWidth > p2Wrap.offsetWidth || p2Wrap.scrollHeight > p2Wrap.offsetHeight){
							var newFontSize = parseInt(parseFloat($("#p2Name").css('font-size').slice(0,-2)) * .95) + 'px';
							$('#p2Name').css('font-size', newFontSize);
							var newTeamFontSize = parseInt(parseFloat($("#p2Team").css('font-size').slice(0,-2)) * .95) + 'px';
							$("#p2Team").css('font-size', newTeamFontSize);
						}
					});
					
					TweenMax.to('#p2Wrapper',.3,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:.2});
				}});
			}
			
			if($('#round').text() != round){
				TweenMax.to('#round',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){ //same format as changing names just no change in positioning, only fade in/out
					$('#round').html(round);
					TweenMax.to('#round',.3,{css:{opacity: 1},ease:Quad.easeOut,delay:.2});
				}});
			}
			
			if($('#p1Score').text() != p1Score){ //same as round, no postioning changes just fade out, update text, fade back in
				TweenMax.to('#p1Score',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
					$('#p1Score').html(p1Score);
					
					TweenMax.to('#p1Score',.3,{css:{opacity: 1},ease:Quad.easeOut,delay:.2});
				}});
			}
			
			if($('#p2Score').text() != p2Score){
				TweenMax.to('#p2Score',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
					$('#p2Score').html(p2Score);
					
					TweenMax.to('#p2Score',.3,{css:{opacity: 1},ease:Quad.easeOut,delay:.2});
				}});
			}

			if($('#result1').text() != resultScore1){
                TweenMax.to('#result1',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
                    $('#result1').html(resultScore1);
					if (resultScore1.length > 1) {
						$('#result1').css("fontSize", "35px");
					} else {
						$('#result1').css("fontSize", resultScoreSize);
					}
                    TweenMax.to('#result1',.3,{css:{opacity: 1},ease:Quad.easeOut,delay:.2});
                }});
            }

            if($('#result2').text() != resultScore2){
                TweenMax.to('#result2',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
                    $('#result2').html(resultScore2);
					if (resultScore2.length > 1) {
						$('#result2').css("fontSize", "35px");
					} else {
						$('#result2').css("fontSize", resultScoreSize);
					}
                    TweenMax.to('#result2',.3,{css:{opacity: 1},ease:Quad.easeOut,delay:.2});
                }});
            }

			if($('#result1Name').text() != resultPlayer1){
                TweenMax.to('#results1',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
                    $('#result1Name').css('font-size',resultNameSize).html(resultPlayer1);

                    p1Result.each(function(i, p1Result){
                        while(p1Result.scrollWidth > p1Result.offsetWidth || p1Result.scrollHeight > p1Result.offsetHeight){
                            var newFontSize = parseInt(parseFloat($('#result1Name').css('font-size').slice(0,-2)) * .95) + 'px';
                            $('#result1Name').css('font-size', newFontSize);
                        }
                    });

                    TweenMax.to('#results1',.3,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:.2});
                }});
            }
            if($('#result2Name').text() != resultPlayer2){
                TweenMax.to('#results2',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
                    $('#result2Name').css('font-size',resultNameSize).html(resultPlayer2);

                    p2Result.each(function(i, p2Result){
                        while(p2Result.scrollWidth > p2Result.offsetWidth || p2Result.scrollHeight > p2Result.offsetHeight){
                            var newFontSize = parseInt(parseFloat($('#result2Name').css('font-size').slice(0,-2)) * .95) + 'px';
                            $('#result2Name').css('font-size', newFontSize);
                        }
                    });

                    TweenMax.to('#results2',.3,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:.2});
                }});
            }

			 if($('#nextPlayer1').text() != nextPlayer1){
                TweenMax.to('#next1',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
                    $('#nextPlayer1').css('font-size',nextNameSize).html(nextPlayer1);

                     next1.each(function(i, next1){
                        while(next1.scrollWidth > next1.offsetWidth || next1.scrollHeight > next1.offsetHeight){
                            var newFontSize = parseInt(parseFloat($('#nextPlayer1').css('font-size').slice(0,-2)) * .95) + 'px';
                            $('#nextPlayer1').css('font-size', newFontSize);
                        }
                    });

                    TweenMax.to('#next1',.3,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:.2});
                }});
            }

             if($('#nextPlayer2').text() != nextPlayer2){
                TweenMax.to('#next2',.3,{css:{opacity: 0},ease:Quad.easeOut,delay:0,onComplete:function(){
                    $('#nextPlayer2').css('font-size',nextNameSize).html(nextPlayer2);

                     next2.each(function(i, next2){
                        while(next2.scrollWidth > next2.offsetWidth || next2.scrollHeight > next2.offsetHeight){
                            var newFontSize = parseInt(parseFloat($('#nextPlayer2').css('font-size').slice(0,-2)) * .95) + 'px';
                            $('#nextPlayer2').css('font-size', newFontSize);
                        }
                    });

                    TweenMax.to('#next2',.3,{css:{x: '+0px', opacity: 1},ease:Quad.easeOut,delay:.2});
                }});
            }


			if(countryHold1 != p1Country){
				TweenMax.to("#f1Wrapper",.3,{css:{opacity: 0},delay:0,onComplete:function(){
					$("#p1Country").attr("src","../imgs/countries/"+countryFlag(p1Country)+".png").on("error",function(){
						$("#p1Country").attr("src","../imgs/countries/world.png");
					});
					countryHold1 = p1Country;
					TweenMax.to("#f1Wrapper",.3,{css:{opacity: 1},delay:.2});
				}});
			}
			
			if(countryHold2 != p2Country){
				TweenMax.to("#f2Wrapper",.3,{css:{opacity: 0},delay:0,onComplete:function(){
					$("#p2Country").attr("src","../imgs/countries/"+countryFlag(p2Country)+".png").on("error",function(){
						$("#p2Country").attr("src","../imgs/countries/world.png");
					});
					countryHold2 = p2Country;
					TweenMax.to("#f2Wrapper",.3,{css:{opacity: 1},delay:.2});
				}});
			}
			
			if(gameHold != game){ //checks to see if current json value for 'game' has changed from what is stored in gameHold html object
				TweenMax.to('#scoreboardBG',.3,{css:{opacity: 0},delay:0});
				TweenMax.to('#scoreboard',.3,{css:{opacity: 0},delay:0}); //hide scoreboard background, scoreboard text, and logos
				TweenMax.to('.logos',.3,{css:{opacity: 0},delay:0,onComplete:function(){ //then execute function
					gameHold = game; //updates gameHold html object with new game dropdown value
			
					if(game == 'BBTAG' || game == 'SFVAE' || game == 'TEKKEN7' || game == 'UNIST'){
						$('#scoreboardVid').attr('src','../webm/scoreboard_1.webm');
						TweenMax.set('#leftWrapper',{css:{y: '+0px'}}); //same functions as above but this time also return wrappers to original positioning
						TweenMax.set('#rightWrapper',{css:{y: '+0px'}});
					}
					else if(game == 'BBCF' || game == 'DBFZ' || game == 'GGXRD' || game == 'KOFXIV' || game == 'MVCI' || game == 'UMVC3'){
						$('#scoreboardVid').attr('src','../webm/scoreboard_2.webm');
						TweenMax.set('#leftWrapper',{css:{y: adjust2}});
						TweenMax.set('#rightWrapper',{css:{y: adjust2}});
					}
					else if(game == 'USF4'){
						$('#scoreboardVid').attr('src','../webm/scoreboard_3.webm');
						TweenMax.set('#leftWrapper',{css:{y: adjust3}});
						TweenMax.set('#rightWrapper',{css:{y: adjust3}});
					}
					else{				
						$('#scoreboardVid').attr('src','../webm/scoreboard_2.webm');
						TweenMax.set('#leftWrapper',{css:{y: adjust2}});
						TweenMax.set('#rightWrapper',{css:{y: adjust2}});
					}
					if(game == 'BBTAG' || game == 'UNIST'){
						var adjustLgW = parseFloat(adjustLg[3]) * adjustLg[2]; //var changed so that it bases resized on original logo size rather than current value
						var adjustLgH = parseFloat(adjustLg[4]) * adjustLg[2]; //uses variables stored in the 'adjustLg' array in scoreboard.html
						TweenMax.set('.logos',{css:{x: adjustLg[0], y: adjustLg[1], width: adjustLgW, height: adjustLgH}});
					}
					else{
						TweenMax.set('.logos',{css:{x: '+0px', y: '+0px', width: adjustLg[3], height: adjustLg[4]}}); //also return logos to original positioning and size
					}
					
					//document.getElementById('scoreboardVid').play(); //plays out scoreboard video to reload back to end status
					
					TweenMax.to('#scoreboardBG',.3,{css:{opacity: 1},delay:.5}); //fade background/text objects back in with enough delay for scoreboard to finish playing first
					TweenMax.to('#scoreboard',.3,{css:{opacity: 1},delay:.5});
					TweenMax.to('.logos',.3,{css:{opacity: .7},delay:.5}); //TweenMax to fade logos back in, note to fade them to same opacity as default in CSS
				}});
			}
		}
	}
	
	function logoLoop(){
		var initialTime = 700; //initial fade-in time for first logo
		var intervalTime = 15000; //amount of time between changing of logos
		var fadeTime = 2000; //duration of crossfade between logos
		var currentItem = 0; //placement value within logoWrapper container of current logo being operated on in function
		var itemCount = $('#logoWrapper').children().length; //number of logo <img> objects located within logoWrapper container
		
		if(itemCount > 1){
			$('#logoWrapper').find('img').eq(currentItem).fadeIn(initialTime);
			
			setInterval(function(){
				
				$('#logoWrapper').find('img').eq(currentItem).fadeOut(fadeTime);
			
				if(currentItem == itemCount - 1){
					currentItem = 0;
				}
				else{
					currentItem++;
				}
				
				$('#logoWrapper').find('img').eq(currentItem).fadeIn(fadeTime);
				
			},intervalTime);
		}
		else{
			$('.logos').fadeIn(initialTime);
		}
	}
}