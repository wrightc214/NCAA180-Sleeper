(function(){"use strict";
var a=window.NCAA180&&window.NCAA180.access;if(!a)return;
var ids=["mode","good","bad","motion","emphasis"],el=function(id){return document.getElementById(id);};
function render(){var s=a.read();el("mode").value=s.mode;el("good").value=s.custom.good;el("bad").value=s.custom.bad;el("motion").value=s.motion;el("emphasis").checked=s.emphasis;el("good-value").textContent=s.custom.good;el("bad-value").textContent=s.custom.bad;
var warnings=[];var needs=false;if(s.mode==="custom"){var light=a.contrast(s.custom.good,"#ffffff")<4.5||a.contrast(s.custom.bad,"#ffffff")<4.5;var dark=a.contrast(s.custom.good,"#171b22")<4.5||a.contrast(s.custom.bad,"#171b22")<4.5;var fill=light;needs=light||dark;if(light)warnings.push("Selected colours may be difficult to read on light backgrounds.");if(dark)warnings.push("Selected colours may be difficult to read on dark backgrounds.");if(fill)warnings.push("White text on solid fills may be difficult to read.");if(a.contrast(s.custom.good,s.custom.bad)<1.5)warnings.push("Positive and negative colours may be difficult to distinguish; automatic contrast correction cannot guarantee distinguishability.");}el("contrast-option").hidden=!(s.mode==="custom"&&needs);el("auto-contrast").checked=s.autoContrast;el("warnings").textContent=warnings.length?"Warning: "+warnings.join(" ")+(s.autoContrast?" Automatic correction is on where needed.":" Your exact selected colours are displayed; correction is off."):"";el("good").disabled=s.mode!=="custom";el("bad").disabled=s.mode!=="custom";}
el("mode").addEventListener("change",function(){a.save({mode:this.value});render();});
el("motion").addEventListener("change",function(){a.save({motion:this.value});render();});
el("emphasis").addEventListener("change",function(){a.save({emphasis:this.checked});render();});
el("auto-contrast").addEventListener("change",function(){a.save({autoContrast:this.checked});render();});
["good","bad"].forEach(function(k){el(k).addEventListener("input",function(){var o={};o[k]=this.value;a.save({mode:"custom",custom:o});render();});});
el("restore-custom").addEventListener("click",function(){a.save({custom:{bad:a.defaults.custom.bad,good:a.defaults.custom.good}});render();});
el("reset-all").addEventListener("click",function(){a.reset();render();});
window.addEventListener("ncaa180:accesschange",render);
render();
})();