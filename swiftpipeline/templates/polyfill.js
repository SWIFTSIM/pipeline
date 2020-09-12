/* Disable minification (remove `.min` from URL path) for more info */

{% raw %}

(function(self, undefined) {function Get(n,t){return n[t]}function ToBoolean(o){return Boolean(o)}function Type(e){switch(typeof e){case"undefined":return"undefined";case"boolean":return"boolean";case"number":return"number";case"string":return"string";case"symbol":return"symbol";default:return null===e?"null":"Symbol"in self&&(e instanceof self.Symbol||e.constructor===self.Symbol)?"symbol":"object"}}Object.defineProperty(RegExp.prototype,"flags",{configurable:!0,enumerable:!1,get:function(){var e=this;if("object"!==Type(e))throw new TypeError("Method called on incompatible type: must be an object.");var o="";return ToBoolean(Get(e,"global"))&&(o+="g"),ToBoolean(Get(e,"ignoreCase"))&&(o+="i"),ToBoolean(Get(e,"multiline"))&&(o+="m"),ToBoolean(Get(e,"unicode"))&&(o+="u"),ToBoolean(Get(e,"sticky"))&&(o+="y"),o}});})('object' === typeof window && window || 'object' === typeof self && self || 'object' === typeof global && global || {});

{% endraw %}
