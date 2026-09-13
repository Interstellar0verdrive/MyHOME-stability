/* MyHOME calibration panel */
var W=globalThis,D=W.ShadowRoot&&(W.ShadyCSS===void 0||W.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Z=Symbol(),me=new WeakMap,T=class{constructor(e,t,r){if(this._$cssResult$=!0,r!==Z)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(D&&e===void 0){let r=t!==void 0&&t.length===1;r&&(e=me.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),r&&me.set(t,e))}return e}toString(){return this.cssText}},ue=o=>new T(typeof o=="string"?o:o+"",void 0,Z),h=(o,...e)=>{let t=o.length===1?o[0]:e.reduce((r,n,i)=>r+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+o[i+1],o[0]);return new T(t,o,Z)},ge=(o,e)=>{if(D)o.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let r=document.createElement("style"),n=W.litNonce;n!==void 0&&r.setAttribute("nonce",n),r.textContent=t.cssText,o.appendChild(r)}},Q=D?o=>o:o=>o instanceof CSSStyleSheet?(e=>{let t="";for(let r of e.cssRules)t+=r.cssText;return ue(t)})(o):o;var{is:ot,defineProperty:nt,getOwnPropertyDescriptor:it,getOwnPropertyNames:st,getOwnPropertySymbols:at,getPrototypeOf:lt}=Object,j=globalThis,ve=j.trustedTypes,pt=ve?ve.emptyScript:"",ct=j.reactiveElementPolyfillSupport,M=(o,e)=>o,ee={toAttribute(o,e){switch(e){case Boolean:o=o?pt:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,e){let t=o;switch(e){case Boolean:t=o!==null;break;case Number:t=o===null?null:Number(o);break;case Object:case Array:try{t=JSON.parse(o)}catch{t=null}}return t}},ye=(o,e)=>!ot(o,e),fe={attribute:!0,type:String,converter:ee,reflect:!1,useDefault:!1,hasChanged:ye};Symbol.metadata??=Symbol("metadata"),j.litPropertyMetadata??=new WeakMap;var f=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=fe){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let r=Symbol(),n=this.getPropertyDescriptor(e,r,t);n!==void 0&&nt(this.prototype,e,n)}}static getPropertyDescriptor(e,t,r){let{get:n,set:i}=it(this.prototype,e)??{get(){return this[t]},set(a){this[t]=a}};return{get:n,set(a){let c=n?.call(this);i?.call(this,a),this.requestUpdate(e,c,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??fe}static _$Ei(){if(this.hasOwnProperty(M("elementProperties")))return;let e=lt(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(M("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(M("properties"))){let t=this.properties,r=[...st(t),...at(t)];for(let n of r)this.createProperty(n,t[n])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[r,n]of t)this.elementProperties.set(r,n)}this._$Eh=new Map;for(let[t,r]of this.elementProperties){let n=this._$Eu(t,r);n!==void 0&&this._$Eh.set(n,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let r=new Set(e.flat(1/0).reverse());for(let n of r)t.unshift(Q(n))}else e!==void 0&&t.push(Q(e));return t}static _$Eu(e,t){let r=t.attribute;return r===!1?void 0:typeof r=="string"?r:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let r of t.keys())this.hasOwnProperty(r)&&(e.set(r,this[r]),delete this[r]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ge(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,r){this._$AK(e,r)}_$ET(e,t){let r=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,r);if(n!==void 0&&r.reflect===!0){let i=(r.converter?.toAttribute!==void 0?r.converter:ee).toAttribute(t,r.type);this._$Em=e,i==null?this.removeAttribute(n):this.setAttribute(n,i),this._$Em=null}}_$AK(e,t){let r=this.constructor,n=r._$Eh.get(e);if(n!==void 0&&this._$Em!==n){let i=r.getPropertyOptions(n),a=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:ee;this._$Em=n;let c=a.fromAttribute(t,i.type);this[n]=c??this._$Ej?.get(n)??c,this._$Em=null}}requestUpdate(e,t,r,n=!1,i){if(e!==void 0){let a=this.constructor;if(n===!1&&(i=this[e]),r??=a.getPropertyOptions(e),!((r.hasChanged??ye)(i,t)||r.useDefault&&r.reflect&&i===this._$Ej?.get(e)&&!this.hasAttribute(a._$Eu(e,r))))return;this.C(e,t,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:r,reflect:n,wrapped:i},a){r&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,a??t??this[e]),i!==!0||a!==void 0)||(this._$AL.has(e)||(this.hasUpdated||r||(t=void 0),this._$AL.set(e,t)),n===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,i]of this._$Ep)this[n]=i;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[n,i]of r){let{wrapped:a}=i,c=this[n];a!==!0||this._$AL.has(n)||c===void 0||this.C(n,void 0,i,c)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(t)):this._$EM()}catch(r){throw e=!1,this._$EM(),r}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};f.elementStyles=[],f.shadowRootOptions={mode:"open"},f[M("elementProperties")]=new Map,f[M("finalized")]=new Map,ct?.({ReactiveElement:f}),(j.reactiveElementVersions??=[]).push("2.1.2");var ae=globalThis,be=o=>o,B=ae.trustedTypes,_e=B?B.createPolicy("lit-html",{createHTML:o=>o}):void 0,Ce="$lit$",b=`lit$${Math.random().toFixed(9).slice(2)}$`,Re="?"+b,dt=`<${Re}>`,$=document,H=()=>$.createComment(""),z=o=>o===null||typeof o!="object"&&typeof o!="function",le=Array.isArray,ht=o=>le(o)||typeof o?.[Symbol.iterator]=="function",te=`[ 	
\f\r]`,O=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,xe=/-->/g,we=/>/g,x=RegExp(`>|${te}(?:([^\\s"'>=/]+)(${te}*=${te}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),$e=/'/g,ke=/"/g,Ee=/^(?:script|style|textarea|title)$/i,pe=o=>(e,...t)=>({_$litType$:o,strings:e,values:t}),s=pe(1),Rt=pe(2),Et=pe(3),k=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Se=new WeakMap,w=$.createTreeWalker($,129);function Ae(o,e){if(!le(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return _e!==void 0?_e.createHTML(e):e}var mt=(o,e)=>{let t=o.length-1,r=[],n,i=e===2?"<svg>":e===3?"<math>":"",a=O;for(let c=0;c<t;c++){let p=o[c],m,u,d=-1,v=0;for(;v<p.length&&(a.lastIndex=v,u=a.exec(p),u!==null);)v=a.lastIndex,a===O?u[1]==="!--"?a=xe:u[1]!==void 0?a=we:u[2]!==void 0?(Ee.test(u[2])&&(n=RegExp("</"+u[2],"g")),a=x):u[3]!==void 0&&(a=x):a===x?u[0]===">"?(a=n??O,d=-1):u[1]===void 0?d=-2:(d=a.lastIndex-u[2].length,m=u[1],a=u[3]===void 0?x:u[3]==='"'?ke:$e):a===ke||a===$e?a=x:a===xe||a===we?a=O:(a=x,n=void 0);let y=a===x&&o[c+1].startsWith("/>")?" ":"";i+=a===O?p+dt:d>=0?(r.push(m),p.slice(0,d)+Ce+p.slice(d)+b+y):p+b+(d===-2?c:y)}return[Ae(o,i+(o[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),r]},L=class o{constructor({strings:e,_$litType$:t},r){let n;this.parts=[];let i=0,a=0,c=e.length-1,p=this.parts,[m,u]=mt(e,t);if(this.el=o.createElement(m,r),w.currentNode=this.el.content,t===2||t===3){let d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(n=w.nextNode())!==null&&p.length<c;){if(n.nodeType===1){if(n.hasAttributes())for(let d of n.getAttributeNames())if(d.endsWith(Ce)){let v=u[a++],y=n.getAttribute(d).split(b),N=/([.?@])?(.*)/.exec(v);p.push({type:1,index:i,name:N[2],strings:y,ctor:N[1]==="."?oe:N[1]==="?"?ne:N[1]==="@"?ie:C}),n.removeAttribute(d)}else d.startsWith(b)&&(p.push({type:6,index:i}),n.removeAttribute(d));if(Ee.test(n.tagName)){let d=n.textContent.split(b),v=d.length-1;if(v>0){n.textContent=B?B.emptyScript:"";for(let y=0;y<v;y++)n.append(d[y],H()),w.nextNode(),p.push({type:2,index:++i});n.append(d[v],H())}}}else if(n.nodeType===8)if(n.data===Re)p.push({type:2,index:i});else{let d=-1;for(;(d=n.data.indexOf(b,d+1))!==-1;)p.push({type:7,index:i}),d+=b.length-1}i++}}static createElement(e,t){let r=$.createElement("template");return r.innerHTML=e,r}};function S(o,e,t=o,r){if(e===k)return e;let n=r!==void 0?t._$Co?.[r]:t._$Cl,i=z(e)?void 0:e._$litDirective$;return n?.constructor!==i&&(n?._$AO?.(!1),i===void 0?n=void 0:(n=new i(o),n._$AT(o,t,r)),r!==void 0?(t._$Co??=[])[r]=n:t._$Cl=n),n!==void 0&&(e=S(o,n._$AS(o,e.values),n,r)),e}var re=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:r}=this._$AD,n=(e?.creationScope??$).importNode(t,!0);w.currentNode=n;let i=w.nextNode(),a=0,c=0,p=r[0];for(;p!==void 0;){if(a===p.index){let m;p.type===2?m=new I(i,i.nextSibling,this,e):p.type===1?m=new p.ctor(i,p.name,p.strings,this,e):p.type===6&&(m=new se(i,this,e)),this._$AV.push(m),p=r[++c]}a!==p?.index&&(i=w.nextNode(),a++)}return w.currentNode=$,n}p(e){let t=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(e,r,t),t+=r.strings.length-2):r._$AI(e[t])),t++}},I=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,r,n){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=r,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=S(this,e,t),z(e)?e===l||e==null||e===""?(this._$AH!==l&&this._$AR(),this._$AH=l):e!==this._$AH&&e!==k&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):ht(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==l&&z(this._$AH)?this._$AA.nextSibling.data=e:this.T($.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:r}=e,n=typeof r=="number"?this._$AC(e):(r.el===void 0&&(r.el=L.createElement(Ae(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===n)this._$AH.p(t);else{let i=new re(n,this),a=i.u(this.options);i.p(t),this.T(a),this._$AH=i}}_$AC(e){let t=Se.get(e.strings);return t===void 0&&Se.set(e.strings,t=new L(e)),t}k(e){le(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,r,n=0;for(let i of e)n===t.length?t.push(r=new o(this.O(H()),this.O(H()),this,this.options)):r=t[n],r._$AI(i),n++;n<t.length&&(this._$AR(r&&r._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let r=be(e).nextSibling;be(e).remove(),e=r}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},C=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,r,n,i){this.type=1,this._$AH=l,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=i,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=l}_$AI(e,t=this,r,n){let i=this.strings,a=!1;if(i===void 0)e=S(this,e,t,0),a=!z(e)||e!==this._$AH&&e!==k,a&&(this._$AH=e);else{let c=e,p,m;for(e=i[0],p=0;p<i.length-1;p++)m=S(this,c[r+p],t,p),m===k&&(m=this._$AH[p]),a||=!z(m)||m!==this._$AH[p],m===l?e=l:e!==l&&(e+=(m??"")+i[p+1]),this._$AH[p]=m}a&&!n&&this.j(e)}j(e){e===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},oe=class extends C{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===l?void 0:e}},ne=class extends C{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==l)}},ie=class extends C{constructor(e,t,r,n,i){super(e,t,r,n,i),this.type=5}_$AI(e,t=this){if((e=S(this,e,t,0)??l)===k)return;let r=this._$AH,n=e===l&&r!==l||e.capture!==r.capture||e.once!==r.once||e.passive!==r.passive,i=e!==l&&(r===l||n);n&&this.element.removeEventListener(this.name,this,r),i&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},se=class{constructor(e,t,r){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(e){S(this,e)}};var ut=ae.litHtmlPolyfillSupport;ut?.(L,I),(ae.litHtmlVersions??=[]).push("3.3.3");var Pe=(o,e,t)=>{let r=t?.renderBefore??e,n=r._$litPart$;if(n===void 0){let i=t?.renderBefore??null;r._$litPart$=n=new I(e.insertBefore(H(),i),i,void 0,t??{})}return n._$AI(o),n};var ce=globalThis,g=class extends f{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Pe(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return k}};g._$litElement$=!0,g.finalized=!0,ce.litElementHydrateSupport?.({LitElement:g});var gt=ce.litElementPolyfillSupport;gt?.({LitElement:g});(ce.litElementVersions??=[]).push("4.2.2");var de={"panel.common.loading":"Loading…","panel.common.all_rooms":"All rooms","panel.common.search":"Search for a shutter","panel.common.room_filter":"Filter by room","panel.common.travel":"travel {travel} cm","panel.common.travel_unknown":"travel not recorded","panel.common.not_yet":"This screen arrives in a later version. Until then “Configure” does everything it will do.","panel.common.offline":"Not connected to Home Assistant.","panel.common.polling":"Live updates are not available on this version; the page refreshes by itself every 30 seconds.","panel.common.action.menu":"Open the sidebar","panel.common.action.configure":"Open Configure instead","panel.common.action.back":"Back to the overview","panel.common.action.close":"Close","panel.common.action.retry":"Try again","panel.overview.title":"Profiles and shutters","panel.overview.gateway":"Gateway {gateway}","panel.overview.intro":"A **profile** describes a type of shutter: how long it takes to run, how long the slats take and how the curtain winds onto the roller. Every shutter can follow one, and Home Assistant scales it to that shutter's own travel.","panel.overview.counts":"There are {profiles} profiles and {covers} basic shutters on this gateway.","panel.overview.group_profile":"Profile “{profile}”","panel.overview.group_none":"No profile","panel.overview.group_none_meta":"Values from the configuration file, or the defaults. This is not an error: a shutter with measurements of its own is perfectly at home here.","panel.overview.group_values":"Reference travel {travel} cm · ascent {up} s · descent {down} s · slats {slat} s","panel.overview.group_values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.group_missing":"This profile is not defined any more: the shutters below have quietly fallen back to their own configuration.","panel.overview.group_from_file":"Defined in the configuration file, and read-only from here.","panel.overview.group_empty":"No shutter in this group.","panel.overview.provenance":"Measured on {cover} · {date}","panel.overview.provenance_unknown":"provenance not recorded","panel.overview.provenance_gone":"Measured on a shutter this gateway no longer has · {date}","panel.overview.provenance_follows":"now follows “{profile}”","panel.overview.count_one":"1 shutter","panel.overview.count_other":"{count} shutters","panel.overview.row_profile_missing":"the profile “{profile}” is not defined any more","panel.overview.row_from_file":"assigned by the configuration file","panel.overview.origin_short_inherited":"Inherited","panel.overview.origin_short_adjusted":"Adjusted","panel.overview.first_run_title":"No profile, for now","panel.overview.first_run_body":"A **profile** describes a type of shutter: how long it takes to run, how long the slats take and how the curtain winds onto the roller. Every shutter can follow one, and Home Assistant scales it to that shutter's own travel.","panel.overview.first_run_more":"A profile is not written, it is measured. Pick one representative shutter and measure it once with the guided calibration — about three minutes. Similar shutters can then follow it.","panel.overview.measure_hint":"The “Configure” dialog opens: that is where the measuring happens. When it is done, the profile appears here.","panel.overview.no_results":"No shutter matches this search.","panel.overview.no_basic_covers":"No basic shutter on this gateway. Advanced shutters report their own position, so there is no travel model to measure.","panel.overview.action.measure":"Measure a shutter ↗","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.action.open_profile":"Open the profile card","panel.overview.action.open_cover":"Open the details of {cover}","panel.overview.handle_label":"Move {cover} to another group or reorder it","panel.overview.handle_inert":"Assignment and reordering arrive in a later version","panel.cover.title":"Shutter “{cover}”","panel.cover.unknown":"This gateway has no shutter with that identifier.","panel.profile.title":"Profile “{profile}”","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.banner.measuring_title":"Measurement in progress","panel.banner.measuring_body":"A guided calibration is using “{cover}”. Until that session ends, this page can only be read: nothing is written from here.","panel.banner.action.resume":"Resume the session ↗","panel.banner.action.terminate":"End it ↗","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.new_text":"new text — to be translated into seven languages","panel.screen.not_in_this_version":"This step belongs to the guided calibration, which moves into the panel in a later version.","panel.screen.motor":"Motor","panel.screen.position":"Estimated position","panel.screen.remaining":"Time remaining ≈ {seconds} s","panel.screen.completed":"Completed","panel.screen.before":"Before","panel.screen.after":"After","panel.screen.action.exit":"Leave the calibration","panel.error.unreachable":"The panel could not read this gateway.","panel.error.unknown_entry":"That gateway is not there any more.","panel.error.entry_not_loaded":"That gateway is configured but not loaded, so its shutters cannot be read.","panel.error.unknown_cover":"That shutter is not on this gateway.","panel.error.advanced_cover":"That shutter reports its own position: there is no travel model to show.","panel.error.busy_calibrating":"A guided calibration is using “{cover}”: nothing can be written until it ends.","panel.error.write_in_progress":"Another change to this gateway is still being applied.","panel.error.profile_not_editable":"The profile “{profile}” is written in the configuration file, which this integration does not change.","panel.error.unknown_profile":"No profile named “{profile}” is stored here.","panel.error.undo_expired":"That change can no longer be taken back.","panel.error.missing_travel":"The travel of {count} shutters is not known yet.","panel.error.invalid_name":"“{profile}” is not a usable profile name: letters, digits and underscores.","panel.error.name_in_use":"“{profile}” is already taken.","panel.error.out_of_range":"{key} must be between {min} and {max}.","panel.error.not_a_number":"{key} takes a number; decimals with a comma or a dot."},Dt=Object.keys(de);var vt="/myhome_static/",ft=/^!\[([^\]]*)\]\(([^)\s]+)\)$/;var q=o=>{let e=[];return o.split("**").forEach((r,n)=>{r&&e.push(n%2===1?s`<strong>${r}</strong>`:s`<span>${r}</span>`)}),e},yt=o=>/^\s*[-*]\s+/.test(o),R=o=>{let e=(o||"").replace(/\r\n/g,`
`).split(/\n{2,}/),t=[];for(let r of e){let n=r.trim();if(!n)continue;let i=ft.exec(n);if(i){t.push(i[2].startsWith(vt)?s`<img class="md-image" src=${i[2]} alt=${i[1]} />`:s`<p>${q(i[1])}</p>`);continue}let a=n.split(`
`);if(a.every(yt)){t.push(s`<ul>
          ${a.map(c=>s`<li>${q(c.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}t.push(s`<p>
        ${a.map((c,p)=>p===0?q(c):[s`<br />`,...q(c)])}
      </p>`)}return s`${t}`};var F=o=>o&&typeof o=="object"&&"code"in o?o:{code:"unknown_error",message:String(o)},Te=(o,e)=>o.sendMessagePromise({type:"myhome/calibration/overview",...e?{entry_id:e}:{}}),Me=(o,e)=>o.sendMessagePromise({type:"myhome/calibration/texts",language:e});var Oe=(o,e,t)=>o.subscribeMessage(t,{type:"myhome/calibration/subscribe",...e?{entry_id:e}:{}}),He=o=>F(o).code==="unknown_command";var ze=(o,e)=>{if(!e)return o;let t=o;for(let[r,n]of Object.entries(e))t=t.split(`{${r}}`).join(String(n));return t},_=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this.language="en";this.loaded=!1}async load(e,t){let r=await Me(e,t);this._texts=r.texts??{},this.language=r.language,this.loaded=!0,this._numbers.clear(),this._dates=null}t(e,t){let r=this._lookup(e);if(r!==null)return ze(r,t);let n=de[e];return ze(n??e,t)}md(e,t){return R(this.t(e,t))}origin(e,t){return this.t(`selector.calibration_origin.options.${e}`,{profile:t??""})}number(e,t){let r=this._numbers.get(t);return r||(r=new Intl.NumberFormat(this.language,{minimumFractionDigits:t,maximumFractionDigits:t}),this._numbers.set(t,r)),r.format(e)}date(e){let t=new Date(e);return Number.isNaN(t.getTime())?e:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(t))}_lookup(e){let t=this._texts;for(let r of e.split(".")){if(t===null||typeof t!="object")return null;t=t[r]}return typeof t=="string"?t:null}};var Le=o=>typeof customElements<"u"&&customElements.get(o)!==void 0;var Ie=o=>{o.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var bt={view:"overview",params:{},path:"/"},Ue=o=>{let e="/"+(o||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(e==="/")return bt;let t=e.slice(1).split("/"),r=t.slice(1).join("/"),n=r;try{n=decodeURIComponent(r)}catch{}return t[0]==="cover"&&r?{view:"cover",params:{id:n},path:e}:t[0]==="profile"&&r?{view:"profile",params:{name:n},path:e}:t[0]==="calibrate"&&r?{view:"calibrate",params:{session:n},path:e}:{view:"unknown",params:{},path:e}};var V=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(e){this._onChange=e,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(e){let t=e||"/";if(t===this._fromHost)return;let r=this.current.path;this._fromHost=t,this.current.path!==r&&this._emit()}get current(){let e=typeof location<"u"?location.hash:"";return e&&e.length>1?Ue(e.slice(1)):Ue(this._fromHost)}navigate(e){let t="#"+(e.startsWith("/")?e:"/"+e);location.hash!==t&&(location.hash=t)}_emit(){this._onChange(this.current)}};var _t=o=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:o,search:"",room:"",announce:""}),G=class{constructor(e){this._subscribers=new Set;this._state=_t(e)}get state(){return this._state}subscribe(e){return this._subscribers.add(e),()=>this._subscribers.delete(e)}set(e){this._state={...this._state,...e};for(let t of this._subscribers)t(this._state)}setOverview(e){this.set({overview:e,entryId:e.entry_id,status:"ready",error:null})}setError(e){this.set({status:"error",error:e})}announce(e){this.set({announce:""}),this.set({announce:e})}};var E=h`
  :host {
    /* Project-introduced, with the documented fallbacks. */
    --myhome-text-on-primary: var(--text-primary-color, #ffffff);
    --myhome-snack-action: var(--snack-action-color, #ffc107);

    /* Home Assistant's own, each behind a fallback. */
    --myhome-primary: var(--primary-color, #03a9f4);
    --myhome-accent: var(--accent-color, #ff9800);
    --myhome-text: var(--primary-text-color, #212121);
    --myhome-text-soft: var(--secondary-text-color, #727272);
    --myhome-text-off: var(--disabled-text-color, #bdbdbd);
    --myhome-background: var(--primary-background-color, #fafafa);
    --myhome-background-soft: var(--secondary-background-color, #e5e5e5);
    --myhome-card: var(--card-background-color, #ffffff);
    --myhome-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --myhome-error: var(--error-color, #db4437);
    --myhome-warning: var(--warning-color, #b26b00);
    --myhome-success: var(--success-color, #43a047);
    --myhome-info: var(--info-color, #039be5);
    --myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));
    --myhome-header-text: var(--app-header-text-color, #ffffff);
    --myhome-radius: var(--ha-card-border-radius, 12px);
    --myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, 0.14));

    /* The pastels, at the percentages the handoff fixes. */
    --myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));
    --myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));
    --myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));
    --myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));
    --myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));
    --myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));
    --myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));
    --myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));

    /*
     * The one surface that is not a theme colour, and deliberately so: the wizard's
     * drawings are black line art with a transparent ground, so the area they sit in is
     * the paper they are printed on rather than a card. The handoff fixes it white in
     * both themes for exactly that reason - on a dark card the lines disappear.
     */
    --myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);

    display: block;
    min-height: 100%;
    /* The font comes from the host document; the panel never loads one. */
    color: var(--myhome-text);
    background: var(--myhome-background);
  }

  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }

  :host * :focus-visible {
    outline: 2px solid var(--myhome-primary);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    :host * {
      animation-duration: 0.001ms !important;
      transition-duration: 0.001ms !important;
    }
  }
`,A=h`
  .card {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
  }
`,P=h`
  .cta {
    min-height: 48px;
    padding: 0 24px;
    border-radius: 24px;
    border: none;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    font: inherit;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
  }

  .cta.secondary {
    background: transparent;
    border: 1px solid var(--myhome-primary);
    color: var(--myhome-primary);
  }

  .cta.text {
    background: transparent;
    border: none;
    color: var(--myhome-primary);
    padding: 0 12px;
  }

  .cta.destructive {
    background: var(--myhome-error-strong);
    color: var(--myhome-error);
  }

  .cta[disabled] {
    background: var(--myhome-background-soft);
    color: var(--myhome-text-off);
    cursor: default;
  }

  .cta.compact {
    min-height: 44px;
    padding: 0 18px;
    border-radius: 22px;
    font-size: 14px;
  }
`,K=h`
  .field {
    height: 44px;
    border-radius: 8px;
    border: 1px solid var(--myhome-divider);
    background: var(--myhome-card);
    color: var(--myhome-text);
    padding: 0 12px;
    font: inherit;
    font-size: 14px;
  }

  .field:disabled {
    color: var(--myhome-text-off);
  }
`,X=h`
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0 0 0 0);
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }
`;var Ne=o=>s`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${o}</div>`;var We=h`
  .measuring {
    max-width: 1200px;
    margin: 16px auto 0;
    padding: 12px 16px;
    border-radius: var(--myhome-radius);
    background: var(--myhome-warning-pastel);
    display: flex;
    gap: 12px;
    align-items: baseline;
    flex-wrap: wrap;
  }

  .measuring strong {
    color: var(--myhome-warning);
    font-weight: 500;
  }

  .measuring .body {
    flex: 1 1 320px;
    line-height: 1.5;
  }

  .measuring .links {
    display: flex;
    gap: 16px;
  }

  .measuring a {
    color: var(--myhome-primary);
    min-height: 44px;
    display: inline-flex;
    align-items: center;
  }
`,De=(o,e,t)=>s`<div class="measuring" role="status" aria-live="polite">
    <strong>${o.t("panel.banner.measuring_title")}</strong>
    <span class="body">${o.t("panel.banner.measuring_body",{cover:e})}</span>
    <span class="links">
      <a href=${t}>${o.t("panel.banner.action.resume")}</a>
      <a href=${t}>${o.t("panel.banner.action.terminate")}</a>
    </span>
  </div>`;var je=h`
  .chip {
    font-size: 12px;
    border-radius: 10px;
    padding: 3px 9px;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: var(--myhome-background-soft);
    color: var(--myhome-text-soft);
  }

  .chip.measured {
    background: var(--myhome-primary-pastel);
    color: var(--myhome-text);
  }

  .chip.adjusted {
    background: var(--myhome-accent-pastel);
    color: var(--myhome-text);
  }

  .chip .dot {
    width: 6px;
    height: 6px;
    border-radius: 3px;
    background: var(--myhome-accent);
    display: inline-block;
  }
`,Be=(o,e,t,r)=>{let n=e==="measured"?"measured":e==="adjusted"?"adjusted":"neutral",i;return r&&e==="inherited"?i=o.t("panel.overview.origin_short_inherited"):r&&e==="adjusted"?i=o.t("panel.overview.origin_short_adjusted"):i=o.origin(e,t),s`<span class="chip ${n}"
    >${n==="adjusted"?s`<span class="dot" aria-hidden="true"></span>`:l}${i}</span
  >`};var qe=h`
  .row {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px;
    border-radius: 8px;
    min-height: 48px;
  }

  .row .divider {
    position: absolute;
    left: 8px;
    right: 8px;
    top: -1px;
    height: 1px;
    background: var(--myhome-divider);
    opacity: 0.6;
    pointer-events: none;
  }

  .row .handle {
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    cursor: grab;
    font-size: 18px;
    letter-spacing: 2px;
    border-radius: 8px;
    touch-action: none;
    -webkit-user-select: none;
    user-select: none;
  }

  .row .handle[disabled] {
    cursor: default;
    color: var(--myhome-text-off);
  }

  @media (max-width: 599px) {
    .row .handle {
      display: none;
    }
  }

  .row .main {
    flex: 1 1 auto;
    min-width: 0;
    text-align: left;
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
    padding: 2px 0;
    border-radius: 6px;
  }

  .row .name {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-size: 14.5px;
    line-height: 1.35;
  }

  .row .sub {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    margin-top: 2px;
  }

  .row .chips {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 6px;
    align-items: center;
  }

  .row .warn {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-warning);
    margin-top: 4px;
  }
`,xt=(o,e)=>{let t=e.height===null?o.t("panel.common.travel_unknown"):o.t("panel.common.travel",{travel:o.number(e.height,0)});return e.area?`${e.area} · ${t}`:t},Fe=(o,e)=>{let{i18n:t}=e;return s`<div class="row" data-row=${o.unique_id}>
    ${e.first?l:s`<div class="divider" aria-hidden="true"></div>`}
    <button
      class="handle"
      type="button"
      disabled
      aria-label=${t.t("panel.overview.handle_label",{cover:o.name})}
      title=${t.t("panel.overview.handle_inert")}
    >
      ⠿
    </button>
    <button
      class="main"
      type="button"
      title=${o.name}
      aria-label=${t.t("panel.overview.action.open_cover",{cover:o.name})}
      @click=${()=>e.onOpen(o)}
    >
      <span class="name">${o.name}</span>
      <span class="sub">${xt(t,o)}</span>
      <span class="chips">
        ${Be(t,o.origin,o.profile,e.short)}
      </span>
      ${o.profile_missing?s`<span class="warn"
            >${t.t("panel.overview.row_profile_missing",{profile:o.profile??""})}</span
          >`:l}
      ${o.profile_from_file&&!o.profile_missing?s`<span class="sub">${t.t("panel.overview.row_from_file")}</span>`:l}
    </button>
  </div>`};var Ve=h`
  .groups {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /*
   * From 600 px the groups stand side by side and the row of them scrolls sideways, which
   * is what makes a drag between two profiles one gesture (lot 7). Below it they stack.
   */
  @media (min-width: 600px) {
    .groups {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(300px, 1fr);
      gap: 16px;
      align-items: start;
      overflow-x: auto;
      padding-bottom: 8px;
    }
  }

  .group {
    position: relative;
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
  }

  .group-head {
    padding: 16px 16px 12px;
    border-bottom: 1px solid var(--myhome-divider);
  }

  .group-head .line {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }

  .group-head h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 500;
    flex: 1 1 auto;
    min-width: 0;
  }

  .group-head h2 button {
    border: none;
    background: transparent;
    color: var(--myhome-primary);
    font: inherit;
    cursor: pointer;
    padding: 0;
    min-height: 28px;
    text-align: left;
  }

  .group-head .count {
    color: var(--myhome-text-soft);
    font-size: 13px;
  }

  .group-head .meta {
    margin: 6px 0 0;
    font-size: 13px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .group-head .meta.second {
    margin-top: 4px;
  }

  .group-head .meta.warn {
    color: var(--myhome-warning);
  }

  .group-body {
    display: flex;
    flex-direction: column;
    padding: 8px;
    gap: 2px;
    min-height: 56px;
  }

  .group-body .empty {
    margin: 8px;
    font-size: 13px;
    color: var(--myhome-text-soft);
  }
`,Ge=(o,e)=>{let{i18n:t}=e,r=o.covers.length===1?t.t("panel.overview.count_one"):t.t("panel.overview.count_other",{count:o.covers.length});return s`<section class="group" data-group=${o.key??"none"} aria-labelledby=${o.id}>
    <div class="group-head">
      <div class="line">
        <h2 id=${o.id}>
          ${o.key===null?o.title:s`<button
                type="button"
                title=${t.t("panel.overview.action.open_profile")}
                @click=${()=>e.onOpenProfile(o.key)}
              >
                ${o.title}
              </button>`}
        </h2>
        <span class="count">${r}</span>
      </div>
      ${o.values?s`<p class="meta">${o.values}</p>`:l}
      ${o.warning?s`<p class="meta second warn">${o.warning}</p>`:o.provenance?s`<p class="meta second">${o.provenance}</p>`:l}
    </div>
    <div class="group-body">
      ${o.covers.map((n,i)=>Fe(n,{i18n:t,short:n.profile===o.key,first:i===0,onOpen:e.onOpenCover}))}
      ${o.covers.length===0?s`<p class="empty">${t.t("panel.overview.group_empty")}</p>`:l}
    </div>
  </section>`};var U="/config/integrations/integration/myhome",J=class extends g{static{this.properties={i18n:{attribute:!1},overview:{attribute:!1},search:{type:String},room:{type:String}}}constructor(){super(),this.i18n=new _,this.overview=null,this.search="",this.room=""}static{this.styles=[E,A,P,K,je,qe,Ve,h`
      :host {
        display: block;
        background: transparent;
      }

      .intro {
        margin: 8px 0 4px;
        max-width: 72ch;
      }

      .intro p {
        margin: 0 0 8px;
        line-height: 1.55;
      }

      .counts {
        margin: 0 0 16px;
        color: var(--myhome-text-soft);
      }

      .controls {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
        margin: 0 0 16px;
      }

      .controls .search {
        flex: 1 1 220px;
        max-width: 340px;
      }

      .controls .spacer {
        flex: 1 1 auto;
      }

      /*
       * The select draws its own arrow: only with appearance stripped does it take the
       * theme's own background and text colours, and the native arrow goes with it.
       */
      select.field {
        appearance: none;
        padding-right: 36px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%23888888' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right 12px center;
      }

      a.cta {
        display: inline-flex;
        align-items: center;
        text-decoration: none;
      }

      .welcome {
        max-width: 640px;
        margin: 48px auto;
        padding: 32px;
      }

      .welcome h2 {
        margin: 0 0 12px;
        font-size: 22px;
        font-weight: 500;
      }

      .welcome p {
        margin: 0 0 8px;
        line-height: 1.55;
      }

      .welcome .soft {
        color: var(--myhome-text-soft);
        margin-bottom: 24px;
      }

      .welcome .after {
        margin: 12px 0 0;
        font-size: 13px;
        color: var(--myhome-text-soft);
      }

      .notice {
        padding: 16px;
        margin: 16px 0;
        font-size: 14px;
        line-height: 1.55;
      }

      .notice .actions {
        margin-top: 12px;
      }
    `]}_fire(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}get _rooms(){let e=new Set;for(let t of this.overview?.covers??[])t.area&&e.add(t.area);return Array.from(e).sort((t,r)=>t.localeCompare(r,this.i18n.language))}_matches(e){let t=this.search.trim().toLowerCase();return t&&!e.name.toLowerCase().includes(t)?!1:!this.room||e.area===this.room}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group_values_unknown"):this.i18n.t("panel.overview.group_values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),up:this.i18n.number(e.values.opening_time,1),down:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml")return this.i18n.t("panel.overview.group_from_file");if(!e.measured_on)return this.i18n.t("panel.overview.provenance_unknown");let t=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.provenance_gone",{date:t});let r=this.i18n.t("panel.overview.provenance",{cover:e.measured_on_name,date:t}),n=(this.overview?.covers??[]).find(i=>i.unique_id===e.measured_on);if(n&&n.profile!==e.name){let i=n.profile??this.i18n.t("panel.overview.group_none");r+=` · ${this.i18n.t("panel.overview.provenance_follows",{profile:i})}`}return r}get _groups(){let e=this.overview;if(!e)return[];let t=[...e.covers].sort((i,a)=>i.order_index-a.order_index),r=i=>t.filter(a=>(a.profile??null)===i&&this._matches(a)),n=e.profiles.map((i,a)=>({key:i.name,id:`group-${a}`,title:this.i18n.t("panel.overview.group_profile",{profile:i.name}),values:this._valuesLine(i),provenance:this._provenanceLine(i),warning:i.missing?this.i18n.t("panel.overview.group_missing"):"",covers:r(i.name)}));return n.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group_none"),values:this.i18n.t("panel.overview.group_none_meta"),provenance:"",warning:"",covers:r(null)}),n}_renderControls(){return s`<div class="controls">
      <input
        class="field search"
        type="search"
        .value=${this.search}
        placeholder=${this.i18n.t("panel.common.search")}
        aria-label=${this.i18n.t("panel.common.search")}
        @input=${e=>this._fire("myhome-search",e.target.value)}
      />
      <select
        class="field"
        aria-label=${this.i18n.t("panel.common.room_filter")}
        .value=${this.room}
        @change=${e=>this._fire("myhome-room",e.target.value)}
      >
        <option value="">${this.i18n.t("panel.common.all_rooms")}</option>
        ${this._rooms.map(e=>s`<option value=${e}>${e}</option>`)}
      </select>
      <span class="spacer"></span>
      <a class="cta secondary compact" href=${U} title=${this.i18n.t("panel.overview.measure_hint")}
        >${this.i18n.t("panel.overview.action.measure")}</a
      >
    </div>`}_renderFirstRun(){return s`<section class="card welcome">
      <h2>${this.i18n.t("panel.overview.first_run_title")}</h2>
      <div>${this.i18n.md("panel.overview.first_run_body")}</div>
      <div class="soft">${this.i18n.md("panel.overview.first_run_more")}</div>
      <a class="cta" href=${U}>${this.i18n.t("panel.overview.action.measure")}</a>
      <p class="after">${this.i18n.t("panel.overview.measure_hint")}</p>
    </section>`}render(){let e=this.overview;if(!e)return s`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return s`<div class="card notice">
        ${R(this.i18n.t("panel.overview.no_basic_covers"))}
      </div>`;if(e.profiles.length===0)return this._renderFirstRun();let t=this._groups,r=t.reduce((i,a)=>i+a.covers.length,0),n=this.search.trim()!==""||this.room!=="";return s`
      <div class="intro">${this.i18n.md("panel.overview.intro")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.counts",{profiles:e.profiles.length,covers:e.covers.length})}
      </p>
      ${this._renderControls()}
      ${r===0&&n?s`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${()=>this._fire("myhome-clear-filters")}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`:s`<div class="groups">
            ${t.map(i=>Ge(i,{i18n:this.i18n,onOpenProfile:a=>this._fire("myhome-open-profile",a),onOpenCover:a=>this._fire("myhome-open-cover",a.unique_id)}))}
          </div>`}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",J);var Ke=(o,e)=>o.summary?.note?s`<div class="stub">${o.summary.note}</div>`:l;var Xe=(o,e)=>{let t=o.options??[];return t.length===0?l:s`<div class="options" role="group" aria-label=${o.title}>
    ${t.map(r=>s`<button
        class="option"
        type="button"
        aria-pressed=${r.current?"true":"false"}
        @click=${()=>e.fire(r.action)}
      >
        <span class="option-head">
          <strong class="option-title">${r.title}</strong>
          ${r.chip?s`<span class="chip neutral">${r.chip}</span>`:l}
        </span>
        ${r.meta?s`<span class="option-meta">${r.meta}</span>`:l}
      </button>`)}
  </div>`};var Je=(o,e)=>{let t=o.progress;if(!t)return s`<div class="stub">${e.i18n.t("panel.screen.not_in_this_version")}</div>`;let r=Math.max(0,Math.min(1,t.fraction))*100;return s`<div class="progress-card">
    ${t.text?s`<p class="instruction">${t.text}</p>`:l}
    <div
      class="progress-track"
      role="progressbar"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow=${Math.round(r)}
    >
      <div class="progress-bar" style=${`width:${r}%`}></div>
    </div>
    <p class="progress-eta" role="status">
      ${t.done?e.i18n.t("panel.screen.completed"):t.eta??""}
    </p>
  </div>`};var Ye=(o,e)=>{let t=o.press;if(!t)return s`<div class="stub">${e.i18n.t("panel.screen.not_in_this_version")}</div>`;let r=t.state==="moving";return s`
    ${t.instruction?s`<p class="instruction">${t.instruction}</p>`:l}
    <div class="live">
      <div class="live-row">
        <span class="name">${e.i18n.t("panel.screen.motor")}</span>
        <span class="value ${r?"moving":""}">${t.motor??""}</span>
      </div>
      ${t.position?s`<div class="live-row">
            <span class="name">${e.i18n.t("panel.screen.position")}</span>
            <span class="value">${t.position}</span>
          </div>`:l}
    </div>
    ${t.note?s`<div
          class="note ${t.state==="problem"?"error":"success"}"
          role=${t.state==="problem"?"alert":"status"}
        >
          ${t.note}
        </div>`:l}
  `};var Ze=(o,e)=>{let t=o.options??[];if(t.length===0&&!o.field)return s`<div class="stub">${e.i18n.t("panel.screen.not_in_this_version")}</div>`;let r=o.field;return s`
    <div class="options" role="group" aria-label=${o.title}>
      ${t.map(n=>s`<button
          class="option"
          type="button"
          aria-pressed=${n.current?"true":"false"}
          @click=${()=>e.fire(n.action)}
        >
          <strong class="option-title">${n.title}</strong>
          ${n.meta?s`<span class="option-meta">${n.meta}</span>`:l}
        </button>`)}
    </div>
    ${r?s`<div class="reading" style="margin-top:12px">
          <label for="gap">${r.label}</label>
          <div class="row">
            <input
              id="gap"
              inputmode="decimal"
              .value=${r.value}
              placeholder=${r.placeholder??""}
              aria-describedby=${r.error?"gap-error":l}
              aria-invalid=${r.error?"true":"false"}
              @input=${n=>e.fire("field",n.target.value)}
            />
            ${r.unit?s`<span class="unit">${r.unit}</span>`:l}
          </div>
          ${r.error?s`<p class="error" id="gap-error" role="alert">${r.error}</p>`:l}
        </div>`:l}
  `};var Qe=(o,e)=>{let t=o.field;return t?s`<div class="reading ${t.big===!1?"":"big"}">
    <label for="reading">${t.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${t.value}
        placeholder=${t.placeholder??""}
        aria-describedby=${t.error?"reading-error":t.hint?"reading-hint":l}
        aria-invalid=${t.error?"true":"false"}
        @input=${r=>e.fire("field",r.target.value)}
      />
      ${t.unit?s`<span class="unit">${t.unit}</span>`:l}
    </div>
    ${t.hint?s`<p class="hint" id="reading-hint">${t.hint}</p>`:l}
    ${t.error?s`<p class="error" id="reading-error" role="alert">${t.error}</p>`:l}
  </div>`:s`<div class="stub">${e.i18n.t("panel.screen.not_in_this_version")}</div>`};var et=(o,e)=>{let t=o.summary;return t?s`
    <div class="summary">
      ${t.rows.map(r=>s`<div class="summary-row">
          <span class="label">${r.label}</span>
          ${r.before?s`<span class="before" aria-label=${e.i18n.t("panel.screen.before")}
                >${r.before}</span
              >`:l}
          <span class="after" aria-label=${e.i18n.t("panel.screen.after")}>${r.after}</span>
        </div>`)}
      ${t.note?s`<p class="note-line">${t.note}</p>`:l}
    </div>
    ${t.code?s`<pre class="code">${t.code}</pre>`:l}
  `:s`<div class="stub">${e.i18n.t("panel.screen.not_in_this_version")}</div>`};var tt=(o,e)=>o.summary?.rows?.length?s`<div class="summary">
    ${o.summary.rows.map(t=>s`<div class="summary-row">
        <span class="label">${t.label}</span>
        <span class="after">${t.after}</span>
      </div>`)}
    ${o.summary.note?s`<p class="note-line">${o.summary.note}</p>`:l}
  </div>`:l;var rt=h`
  .text-column {
    min-width: 0;
  }

  .phase {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--myhome-text-soft);
  }

  .new-text {
    display: inline-block;
    margin: 0 0 12px;
    background: var(--myhome-info-pastel);
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    color: var(--myhome-text-soft);
  }

  .screen-title {
    margin: 0 0 12px;
    font-size: 20px;
    font-weight: 500;
    line-height: 1.3;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* The outcome screens carry one of four faces, in the pastel of what happened. */
  .outcome-icon {
    width: 32px;
    height: 32px;
    flex: 0 0 32px;
    border-radius: 16px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 600;
  }

  .outcome-icon.saved {
    background: var(--myhome-success-pastel);
    color: var(--myhome-success);
  }

  .outcome-icon.saved::before {
    content: "✓";
  }

  .outcome-icon.cancelled {
    background: var(--myhome-error-pastel);
    color: var(--myhome-error);
  }

  .outcome-icon.cancelled::before {
    content: "✕";
  }

  .outcome-icon.expired {
    background: var(--myhome-warning-pastel);
    color: var(--myhome-warning);
  }

  .outcome-icon.expired::before {
    content: "⧗";
  }

  .outcome-icon.problem {
    background: var(--myhome-error-pastel);
    color: var(--myhome-error);
  }

  .outcome-icon.problem::before {
    content: "!";
  }

  .drawing {
    height: 230px;
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    margin: 0 0 16px;
    background-color: var(--myhome-drawing-paper);
    background-repeat: no-repeat;
  }

  .prose p {
    margin: 0 0 12px;
    font-size: 14.5px;
    line-height: 1.6;
    text-wrap: pretty;
  }

  .prose ul {
    margin: 0 0 12px;
    padding-left: 20px;
    font-size: 14.5px;
    line-height: 1.6;
  }

  .prose .md-image {
    display: block;
    max-width: 100%;
    border-radius: var(--myhome-radius);
    margin: 0 0 12px;
  }

  /* The one big button, 64 px, in the same place on every step. */
  .big {
    width: 100%;
    min-height: 64px;
    border: none;
    border-radius: 16px;
    font: inherit;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    box-shadow: var(--myhome-shadow);
  }

  .big.moving {
    background: var(--myhome-accent);
    color: var(--myhome-text);
  }

  .big[disabled] {
    background: var(--myhome-background-soft);
    color: var(--myhome-text-off);
    cursor: default;
    box-shadow: none;
  }

  .options {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 4px 0 0;
  }

  /*
   * A chosen option gains a border *and* an inset ring rather than a thicker border, so
   * that choosing one does not move the other two (handoff, section 2).
   */
  .option {
    text-align: left;
    border-radius: 10px;
    font: inherit;
    padding: 14px;
    min-height: 56px;
    cursor: pointer;
    color: inherit;
    border: 1px solid var(--myhome-divider);
    background: var(--myhome-card);
  }

  .option[aria-pressed="true"] {
    border-color: var(--myhome-primary);
    box-shadow: inset 0 0 0 1px var(--myhome-primary);
    background: var(--myhome-primary-faint);
  }

  .option .option-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .option .option-title {
    font-weight: 500;
    flex: 1;
    font-size: 14.5px;
    line-height: 1.4;
  }

  .option .option-meta {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    margin-top: 3px;
  }

  .live {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 14px;
  }

  .live-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  .live-row .name {
    color: var(--myhome-text-soft);
  }

  .live-row .value {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }

  /* A motor that is running says so in the warning colour, and keeps saying it. */
  .live-row .value.moving {
    color: var(--myhome-warning);
    animation: myhome-pulse 1.2s ease-in-out infinite;
  }

  @keyframes myhome-pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.55;
    }
  }

  /* The small neutral chip an option can carry, beside its title. */
  .chip {
    font-size: 12px;
    border-radius: 10px;
    padding: 3px 9px;
    white-space: nowrap;
    background: var(--myhome-background-soft);
    color: var(--myhome-text-soft);
  }

  .instruction {
    margin: 0 0 16px;
    font-size: 16.5px;
    line-height: 1.5;
    font-weight: 500;
  }

  .note {
    margin: 14px 0 0;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.55;
  }

  .note.success {
    background: var(--myhome-success-pastel);
  }

  .note.error {
    background: var(--myhome-error-pastel);
  }

  .note.info {
    background: var(--myhome-info-pastel);
  }

  .progress-card {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 16px;
  }

  .progress-track {
    height: 8px;
    border-radius: 4px;
    background: var(--myhome-background-soft);
    overflow: hidden;
  }

  .progress-bar {
    height: 100%;
    background: var(--myhome-primary);
    border-radius: 4px;
    transition: width 0.1s linear;
  }

  .progress-eta {
    margin: 10px 0 0;
    font-size: 13px;
    color: var(--myhome-text-soft);
    font-variant-numeric: tabular-nums;
  }

  .reading {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 16px;
    margin: 4px 0 0;
  }

  .reading label {
    display: block;
    font-size: 13.5px;
    margin: 0 0 8px;
  }

  .reading .row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .reading input {
    flex: 1;
    min-width: 0;
    height: 56px;
    border-radius: 10px;
    border: 1px solid var(--myhome-divider);
    background: var(--myhome-card);
    color: inherit;
    padding: 0 14px;
    font: inherit;
    font-size: 26px;
    font-variant-numeric: tabular-nums;
  }

  .reading.big input {
    height: 64px;
    font-size: 32px;
  }

  .reading .unit {
    font-size: 16px;
    color: var(--myhome-text-soft);
  }

  .reading.big .unit {
    font-size: 18px;
  }

  .reading .hint {
    margin: 8px 0 0;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .reading .error {
    margin: 8px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error);
    line-height: 1.5;
  }

  .summary {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 8px 16px;
    margin: 4px 0 14px;
  }

  .summary-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 9px 0;
    border-bottom: 1px solid var(--myhome-divider);
    font-size: 13.5px;
    flex-wrap: wrap;
  }

  .summary-row:last-of-type {
    border-bottom: none;
  }

  .summary-row .label {
    flex: 1 1 130px;
    color: var(--myhome-text-soft);
  }

  .summary-row .before {
    color: var(--myhome-text-soft);
    font-variant-numeric: tabular-nums;
    text-decoration: line-through;
    opacity: 0.7;
  }

  .summary-row .after {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }

  .summary .note-line {
    margin: 10px 0;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
  }

  .code {
    background: var(--myhome-background-soft);
    border-radius: 8px;
    padding: 12px 14px;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-x: auto;
  }

  .stub {
    margin: 4px 0 0;
    background: var(--myhome-info-pastel);
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 13.5px;
    line-height: 1.55;
  }
`;var Y=class extends g{constructor(){super();this._fire=(t,r)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:t,value:r,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new _}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[E,A,P,K,X,rt,h`
      :host {
        display: block;
        background: transparent;
      }

      .screen {
        width: 100%;
        max-width: 480px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        position: relative;
      }

      main {
        flex: 1;
        padding: 16px 16px 230px;
      }

      .right {
        min-width: 0;
      }

      /*
       * The footer is fixed on a phone, with the gradient the handoff asks for so text
       * scrolling under it fades instead of colliding with it, and it stays above the home
       * indicator.
       */
      .footer {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 480px;
        padding: 36px 16px calc(12px + env(safe-area-inset-bottom, 0px));
        background: linear-gradient(
          to top,
          var(--myhome-background) calc(100% - 36px),
          transparent
        );
        z-index: 25;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      @media (min-width: 900px) {
        .screen {
          max-width: 100%;
        }

        main {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 400px;
          gap: 0 44px;
          align-items: start;
          max-width: 1080px;
          margin: 0 auto;
          padding: 24px 32px 48px;
        }

        /* The pos template has no operative column: one centred column at every width. */
        main.single {
          display: block;
          max-width: 560px;
        }

        .right {
          position: sticky;
          top: 76px;
        }

        .footer {
          position: static;
          transform: none;
          width: auto;
          max-width: none;
          padding: 0;
          background: none;
          margin-top: 20px;
        }
      }
    `]}_renderOperative(t,r){switch(t.model){case"scelta":return Xe(t,r);case"pos":return Je(t,r);case"click":return Ye(t,r);case"controllo":return Ze(t,r);case"metro":return Qe(t,r);case"riepilogo":return et(t,r);case"esito":return tt(t,r);case"lettura":return Ke(t,r);default:return l}}_renderFooter(t,r){let n=t.secondary??[];return!t.primary&&n.length===0?l:s`<div class="footer">
      ${t.primary?s`<button
            class="big ${t.press?.state==="moving"?"moving":""}"
            type="button"
            ?disabled=${t.primary.disabled}
            @click=${()=>this._fire(t.primary.action)}
          >
            ${t.primary.label}
          </button>`:l}
      ${n.map(i=>s`<button
          class="cta ${i.kind==="text"?"text":"secondary"}"
          type="button"
          ?disabled=${i.disabled}
          @click=${()=>r.fire(i.action)}
        >
          ${i.label}
        </button>`)}
    </div>`}render(){let t=this.model;if(!t)return l;let r={i18n:this.i18n,fire:this._fire},n=t.model==="pos";return s`<div class="screen">
      <main class=${n?"single":""}>
        <div class="text-column">
          ${t.phase?s`<p class="phase">
                ${this.i18n.t("panel.screen.phase",{phase:t.phase.label,index:t.phase.index,count:t.phase.count})}
              </p>`:l}
          ${t.newText?s`<p class="new-text">${this.i18n.t("panel.screen.new_text")}</p>`:l}
          <h1 class="screen-title">
            ${t.outcome?s`<span class="outcome-icon ${t.outcome}" aria-hidden="true"></span>`:l}
            <span>${t.title}</span>
          </h1>
          ${t.image?s`<div
                class="drawing"
                role="img"
                aria-label=${t.image.alt}
                style=${`background-image:url("${t.image.src}");background-size:${t.image.size??"100% auto"};background-position:${t.image.pos??"50% 60%"}`}
              ></div>`:l}
          ${t.body?s`<div class="prose">${R(t.body)}</div>`:l}
        </div>
        <div class="right">
          ${this._renderOperative(t,r)} ${this._renderFooter(t,r)}
        </div>
      </main>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",Y);var wt=3e4,he=class extends g{constructor(){super();this._i18n=new _;this._router=new V;this._store=new G(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._onReturn=()=>{!this._started||document.hidden||this._refresh()};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[E,A,P,X,We,h`
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 8px;
        background: var(--myhome-header);
        color: var(--myhome-header-text);
        font-size: 20px;
        font-weight: 400;
        /* The panel handles its own safe area (handle_safe_area: true). */
        padding-top: env(safe-area-inset-top, 0px);
        height: calc(56px + env(safe-area-inset-top, 0px));
      }

      .toolbar .title {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .toolbar .gateway {
        font-size: 13px;
        opacity: 0.8;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 40%;
      }

      /* 48x48, like every target in the handoff. */
      .toolbar button {
        width: 48px;
        height: 48px;
        flex: 0 0 48px;
        border: 0;
        border-radius: 24px;
        background: transparent;
        color: inherit;
        font-size: 20px;
        line-height: 1;
        cursor: pointer;
      }

      .content {
        padding: 16px;
        max-width: 1200px;
        margin: 0 auto;
        padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
      }

      .card.problem {
        background: var(--myhome-error-pastel);
        color: var(--myhome-text);
        padding: 16px;
      }

      .soft {
        color: var(--myhome-text-soft);
        font-size: 13px;
        margin-top: 8px;
      }

      .connection {
        margin: 24px 0 0;
        font-size: 12.5px;
        color: var(--myhome-text-soft);
      }

      a {
        color: var(--myhome-primary);
      }
    `]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(t=>this._store.set({route:t})),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._stopPolling();let t=this._unsubscribeWs;this._unsubscribeWs=null,t?.().catch(()=>{})}shouldUpdate(t){return t.size>1||!t.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(t){if(t.has("route")&&(this._router.setHostPath(this.route?.path),this._store.set({route:this._router.current})),!(!t.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_languageOf(t){return t?.locale?.language||t?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,await this._loadTexts(),await this._refresh(),await this._listen())}async _loadTexts(){let t=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,t)}catch{}this._language=t,this.requestUpdate()}async _refresh(){try{let t=await Te(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(t)}catch(t){this._store.setError(F(t))}}async _listen(){try{this._unsubscribeWs=await Oe(this.hass.connection,this._store.state.entryId,t=>this._onEvent(t)),this._store.set({connection:"live"}),this._stopPolling()}catch(t){He(t)||console.warn("MyHOME panel: live updates are not available",F(t)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(t){if(t.type==="overview"){this._store.setOverview(t.overview);return}if(t.type==="measuring"){let r=this._store.state.overview;if(!r)return;this._store.set({overview:{...r,measuring:t.cover_unique_id?{cover_unique_id:t.cover_unique_id,name:t.name??""}:null}}),this._store.announce(t.cover_unique_id?this._i18n.t("panel.banner.measuring_body",{cover:t.name??""}):"")}}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},wt))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}get _version(){return this.panel?.config?.version??""}_navigate(t){this._router.navigate(t)}_renderMenuButton(){return this.narrow?Le("ha-menu-button")?s`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:s`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>Ie(this)}
    >
      ☰
    </button>`:l}_renderBackButton(){return this._store.state.route.view==="overview"?l:s`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.back")}
      @click=${()=>this._navigate("/")}
    >
      ←
    </button>`}_renderPlaceholder(t,r){let n={id:"panel.common.not_yet",model:"lettura",title:t,body:r,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return s`<myhome-screen
      .model=${n}
      .i18n=${this._i18n}
      @myhome-screen-action=${i=>{i.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}_renderView(){let t=this._store.state;if(t.status==="loading")return s`<div class="card problem" role="status">
        ${this._i18n.t("panel.common.loading")}
      </div>`;if(t.status==="error"||!t.overview){let n=t.error,i=n?.translation_key?`panel.error.${n.translation_key}`:"panel.error.unreachable";return s`<div class="card problem" role="alert">
        <div>${this._i18n.t(i,n?.translation_placeholders??{})}</div>
        <div class="soft">${n?`${n.code}: ${n.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._refresh()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${U}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?s` · ${this._version}`:l}
        </div>
      </div>`}let r=t.route;if(r.view==="cover"){let n=t.overview.covers.find(i=>i.unique_id===r.params.id);return this._renderPlaceholder(n?this._i18n.t("panel.cover.title",{cover:n.name}):this._i18n.t("panel.cover.unknown"),this._i18n.t("panel.common.not_yet"))}if(r.view==="profile"){let n=r.params.name,i=t.overview.profiles.some(a=>a.name===n);return this._renderPlaceholder(i?this._i18n.t("panel.profile.title",{profile:n}):this._i18n.t("panel.profile.unknown"),this._i18n.t("panel.common.not_yet"))}return r.view!=="overview"?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):s`<myhome-overview
      .i18n=${this._i18n}
      .overview=${t.overview}
      .search=${t.search}
      .room=${t.room}
      @myhome-search=${n=>this._store.set({search:n.detail})}
      @myhome-room=${n=>this._store.set({room:n.detail})}
      @myhome-clear-filters=${()=>this._store.set({search:"",room:""})}
      @myhome-open-cover=${n=>this._navigate(`/cover/${encodeURIComponent(n.detail)}`)}
      @myhome-open-profile=${n=>this._navigate(`/profile/${encodeURIComponent(n.detail)}`)}
    ></myhome-overview>`}render(){let t=this._store.state,r=this._i18n.t("panel.overview.title"),n=t.overview?.entries.find(a=>a.entry_id===t.entryId),i=t.overview?.measuring??null;return s`
      <div class="toolbar">
        ${this._renderMenuButton()} ${this._renderBackButton()}
        <div class="title">${r}</div>
        ${n&&(t.overview?.entries.length??0)>1?s`<div class="gateway">
              ${this._i18n.t("panel.overview.gateway",{gateway:n.title})}
            </div>`:l}
      </div>
      ${i?De(this._i18n,i.name,U):l}
      <div class="content">
        ${Ne(t.announce)} ${this._renderView()}
        ${t.connection==="polling"&&t.status==="ready"?s`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:l}
      </div>
    `}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",he);export{he as MyHomeCalibrationPanel};
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
