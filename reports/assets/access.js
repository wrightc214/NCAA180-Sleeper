(function(){"use strict";
var a=window.NCAA180&&window.NCAA180.access;if(!a)return;
var ids=["mode","good","bad","motion","emphasis"],el=function(id){return document.getElementById(id);};
function render(){var s=a.read();el("mode").value=s.mode;el("good").value=s.custom.good;el("bad").value=s.custom.bad;el("motion").value=s.motion;el("emphasis").checked=s.emphasis;el("good-value").textContent=s.custom.good;el("bad-value").textContent=s.custom.bad;
var warnings=[];if(s.mode==="custom"){if(a.contrast(s.custom.good,"#ffffff")<4.5||a.contrast(s.custom.bad,"#ffffff")<4.5)warnings.push("Warning: one or both selected colours may be difficult to read on light backgrounds.");if(a.contrast(s.custom.good,"#171b22")<4.5||a.contrast(s.custom.bad,"#171b22")<4.5)warnings.push("Warning: one or both selected colours may be difficult to read on dark backgrounds.");if(a.contrast(s.custom.good,"#ffffff")<4.5||a.contrast(s.custom.bad,"#ffffff")<4.5)warnings.push("White text on your chosen solid fills may be difficult to read.");if(a.contrast(s.custom.good,s.custom.bad)<1.5)warnings.push("Custom positive and negative colours may be difficult to distinguish.");}el("warnings").textContent=warnings.join(" ") + (warnings.length?" Your colours are saved and displayed exactly as selected.":"");el("good").disabled=s.mode!=="custom";el("bad").disabled=s.mode!=="custom";}
el("mode").addEventListener("change",function(){a.save({mode:this.value});render();});
el("motion").addEventListener("change",function(){a.save({motion:this.value});render();});
el("emphasis").addEventListener("change",function(){a.save({emphasis:this.checked});render();});
["good","bad"].forEach(function(k){el(k).addEventListener("input",function(){var o={};o[k]=this.value;a.save({mode:"custom",custom:o});render();});});
el("restore-custom").addEventListener("click",function(){a.save({custom:{bad:a.defaults.custom.bad,good:a.defaults.custom.good}});render();});
el("reset-all").addEventListener("click",function(){a.reset();render();});
window.addEventListener("ncaa180:accesschange",render);
render();
})();