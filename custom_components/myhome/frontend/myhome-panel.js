/* MyHOME calibration panel */
var le=globalThis,pe=le.ShadowRoot&&(le.ShadyCSS===void 0||le.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Le=Symbol(),it=new WeakMap,G=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==Le)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(pe&&t===void 0){let i=e!==void 0&&e.length===1;i&&(t=it.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&it.set(e,t))}return t}toString(){return this.cssText}},rt=r=>new G(typeof r=="string"?r:r+"",void 0,Le),u=(r,...t)=>{let e=r.length===1?r[0]:t.reduce((i,n,o)=>i+(s=>{if(s._$cssResult$===!0)return s.cssText;if(typeof s=="number")return s;throw Error("Value passed to 'css' function must be a 'css' function result: "+s+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+r[o+1],r[0]);return new G(e,r,Le)},nt=(r,t)=>{if(pe)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let i=document.createElement("style"),n=le.litNonce;n!==void 0&&i.setAttribute("nonce",n),i.textContent=e.cssText,r.appendChild(i)}},Oe=pe?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(let i of t.cssRules)e+=i.cssText;return rt(e)})(r):r;var{is:xi,defineProperty:$i,getOwnPropertyDescriptor:ki,getOwnPropertyNames:Ri,getOwnPropertySymbols:Ei,getPrototypeOf:Pi}=Object,de=globalThis,ot=de.trustedTypes,Si=ot?ot.emptyScript:"",Ci=de.reactiveElementPolyfillSupport,V=(r,t)=>r,ze={toAttribute(r,t){switch(t){case Boolean:r=r?Si:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},at=(r,t)=>!xi(r,t),st={attribute:!0,type:String,converter:ze,reflect:!1,useDefault:!1,hasChanged:at};Symbol.metadata??=Symbol("metadata"),de.litPropertyMetadata??=new WeakMap;var P=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=st){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let i=Symbol(),n=this.getPropertyDescriptor(t,i,e);n!==void 0&&$i(this.prototype,t,n)}}static getPropertyDescriptor(t,e,i){let{get:n,set:o}=ki(this.prototype,t)??{get(){return this[e]},set(s){this[e]=s}};return{get:n,set(s){let p=n?.call(this);o?.call(this,s),this.requestUpdate(t,p,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??st}static _$Ei(){if(this.hasOwnProperty(V("elementProperties")))return;let t=Pi(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(V("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(V("properties"))){let e=this.properties,i=[...Ri(e),...Ei(e)];for(let n of i)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[i,n]of e)this.elementProperties.set(i,n)}this._$Eh=new Map;for(let[e,i]of this.elementProperties){let n=this._$Eu(e,i);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let i=new Set(t.flat(1/0).reverse());for(let n of i)e.unshift(Oe(n))}else t!==void 0&&e.push(Oe(t));return e}static _$Eu(t,e){let i=e.attribute;return i===!1?void 0:typeof i=="string"?i:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return nt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){let i=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,i);if(n!==void 0&&i.reflect===!0){let o=(i.converter?.toAttribute!==void 0?i.converter:ze).toAttribute(e,i.type);this._$Em=t,o==null?this.removeAttribute(n):this.setAttribute(n,o),this._$Em=null}}_$AK(t,e){let i=this.constructor,n=i._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let o=i.getPropertyOptions(n),s=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:ze;this._$Em=n;let p=s.fromAttribute(e,o.type);this[n]=p??this._$Ej?.get(n)??p,this._$Em=null}}requestUpdate(t,e,i,n=!1,o){if(t!==void 0){let s=this.constructor;if(n===!1&&(o=this[t]),i??=s.getPropertyOptions(t),!((i.hasChanged??at)(o,e)||i.useDefault&&i.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(s._$Eu(t,i))))return;this.C(t,e,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:n,wrapped:o},s){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,s??e??this[t]),o!==!0||s!==void 0)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,o]of this._$Ep)this[n]=o;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[n,o]of i){let{wrapped:s}=o,p=this[n];s!==!0||this._$AL.has(n)||p===void 0||this.C(n,void 0,o,p)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(e)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};P.elementStyles=[],P.shadowRootOptions={mode:"open"},P[V("elementProperties")]=new Map,P[V("finalized")]=new Map,Ci?.({ReactiveElement:P}),(de.reactiveElementVersions??=[]).push("2.1.2");var Be=globalThis,lt=r=>r,ce=Be.trustedTypes,pt=ce?ce.createPolicy("lit-html",{createHTML:r=>r}):void 0,vt="$lit$",O=`lit$${Math.random().toFixed(9).slice(2)}$`,gt="?"+O,Ti=`<${gt}>`,F=document,X=()=>F.createComment(""),Z=r=>r===null||typeof r!="object"&&typeof r!="function",We=Array.isArray,Ai=r=>We(r)||typeof r?.[Symbol.iterator]=="function",De=`[ 	
\f\r]`,Y=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,dt=/-->/g,ct=/>/g,H=RegExp(`>|${De}(?:([^\\s"'>=/]+)(${De}*=${De}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ht=/'/g,ut=/"/g,ft=/^(?:script|style|textarea|title)$/i,Ke=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),a=Ke(1),sr=Ke(2),ar=Ke(3),S=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),mt=new WeakMap,N=F.createTreeWalker(F,129);function _t(r,t){if(!We(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return pt!==void 0?pt.createHTML(t):t}var Ii=(r,t)=>{let e=r.length-1,i=[],n,o=t===2?"<svg>":t===3?"<math>":"",s=Y;for(let p=0;p<e;p++){let d=r[p],c,m,h=-1,v=0;for(;v<d.length&&(s.lastIndex=v,m=s.exec(d),m!==null);)v=s.lastIndex,s===Y?m[1]==="!--"?s=dt:m[1]!==void 0?s=ct:m[2]!==void 0?(ft.test(m[2])&&(n=RegExp("</"+m[2],"g")),s=H):m[3]!==void 0&&(s=H):s===H?m[0]===">"?(s=n??Y,h=-1):m[1]===void 0?h=-2:(h=s.lastIndex-m[2].length,c=m[1],s=m[3]===void 0?H:m[3]==='"'?ut:ht):s===ut||s===ht?s=H:s===dt||s===ct?s=Y:(s=H,n=void 0);let f=s===H&&r[p+1].startsWith("/>")?" ":"";o+=s===Y?d+Ti:h>=0?(i.push(c),d.slice(0,h)+vt+d.slice(h)+O+f):d+O+(h===-2?p:f)}return[_t(r,o+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),i]},J=class r{constructor({strings:t,_$litType$:e},i){let n;this.parts=[];let o=0,s=0,p=t.length-1,d=this.parts,[c,m]=Ii(t,e);if(this.el=r.createElement(c,i),N.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(n=N.nextNode())!==null&&d.length<p;){if(n.nodeType===1){if(n.hasAttributes())for(let h of n.getAttributeNames())if(h.endsWith(vt)){let v=m[s++],f=n.getAttribute(h).split(O),D=/([.?@])?(.*)/.exec(v);d.push({type:1,index:o,name:D[2],strings:f,ctor:D[1]==="."?Ne:D[1]==="?"?Fe:D[1]==="@"?qe:B}),n.removeAttribute(h)}else h.startsWith(O)&&(d.push({type:6,index:o}),n.removeAttribute(h));if(ft.test(n.tagName)){let h=n.textContent.split(O),v=h.length-1;if(v>0){n.textContent=ce?ce.emptyScript:"";for(let f=0;f<v;f++)n.append(h[f],X()),N.nextNode(),d.push({type:2,index:++o});n.append(h[v],X())}}}else if(n.nodeType===8)if(n.data===gt)d.push({type:2,index:o});else{let h=-1;for(;(h=n.data.indexOf(O,h+1))!==-1;)d.push({type:7,index:o}),h+=O.length-1}o++}}static createElement(t,e){let i=F.createElement("template");return i.innerHTML=t,i}};function U(r,t,e=r,i){if(t===S)return t;let n=i!==void 0?e._$Co?.[i]:e._$Cl,o=Z(t)?void 0:t._$litDirective$;return n?.constructor!==o&&(n?._$AO?.(!1),o===void 0?n=void 0:(n=new o(r),n._$AT(r,e,i)),i!==void 0?(e._$Co??=[])[i]=n:e._$Cl=n),n!==void 0&&(t=U(r,n._$AS(r,t.values),n,i)),t}var He=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:i}=this._$AD,n=(t?.creationScope??F).importNode(e,!0);N.currentNode=n;let o=N.nextNode(),s=0,p=0,d=i[0];for(;d!==void 0;){if(s===d.index){let c;d.type===2?c=new Q(o,o.nextSibling,this,t):d.type===1?c=new d.ctor(o,d.name,d.strings,this,t):d.type===6&&(c=new Ue(o,this,t)),this._$AV.push(c),d=i[++p]}s!==d?.index&&(o=N.nextNode(),s++)}return N.currentNode=F,n}p(t){let e=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}},Q=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,n){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=U(this,t,e),Z(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==S&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ai(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&Z(this._$AH)?this._$AA.nextSibling.data=t:this.T(F.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:i}=t,n=typeof i=="number"?this._$AC(t):(i.el===void 0&&(i.el=J.createElement(_t(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===n)this._$AH.p(e);else{let o=new He(n,this),s=o.u(this.options);o.p(e),this.T(s),this._$AH=o}}_$AC(t){let e=mt.get(t.strings);return e===void 0&&mt.set(t.strings,e=new J(t)),e}k(t){We(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,i,n=0;for(let o of t)n===e.length?e.push(i=new r(this.O(X()),this.O(X()),this,this.options)):i=e[n],i._$AI(o),n++;n<e.length&&(this._$AR(i&&i._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let i=lt(t).nextSibling;lt(t).remove(),t=i}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},B=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,n,o){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=o,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=l}_$AI(t,e=this,i,n){let o=this.strings,s=!1;if(o===void 0)t=U(this,t,e,0),s=!Z(t)||t!==this._$AH&&t!==S,s&&(this._$AH=t);else{let p=t,d,c;for(t=o[0],d=0;d<o.length-1;d++)c=U(this,p[i+d],e,d),c===S&&(c=this._$AH[d]),s||=!Z(c)||c!==this._$AH[d],c===l?t=l:t!==l&&(t+=(c??"")+o[d+1]),this._$AH[d]=c}s&&!n&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Ne=class extends B{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},Fe=class extends B{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},qe=class extends B{constructor(t,e,i,n,o){super(t,e,i,n,o),this.type=5}_$AI(t,e=this){if((t=U(this,t,e,0)??l)===S)return;let i=this._$AH,n=t===l&&i!==l||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,o=t!==l&&(i===l||n);n&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},Ue=class{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){U(this,t)}};var Mi=Be.litHtmlPolyfillSupport;Mi?.(J,Q),(Be.litHtmlVersions??=[]).push("3.3.3");var wt=(r,t,e)=>{let i=e?.renderBefore??t,n=i._$litPart$;if(n===void 0){let o=e?.renderBefore??null;i._$litPart$=n=new Q(t.insertBefore(X(),o),o,void 0,e??{})}return n._$AI(r),n};var je=globalThis,g=class extends P{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=wt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return S}};g._$litElement$=!0,g.finalized=!0,je.litElementHydrateSupport?.({LitElement:g});var Li=je.litElementPolyfillSupport;Li?.({LitElement:g});(je.litElementVersions??=[]).push("4.2.2");var bt={"panel.assign.action.discard_all":"Discard everything","panel.assign.action.review":"Review and confirm","panel.assign.action.review_hint":"Review and confirm the assignments","panel.assign.action.withdraw":"Withdraw this change","panel.assign.announce.applying":"The changes are being applied.","panel.assign.announce.armed":"Tap the destination group.","panel.assign.announce.discarded":"Every pending change has been discarded.","panel.assign.announce.drag_cancelled":"Drag cancelled.","panel.assign.announce.missing_travel":"Some covers have no travel.","panel.assign.announce.pending":"“{cover}” is pending, towards {target}. Nothing is written yet.","panel.assign.announce.reordered":"Order updated: it will be remembered.","panel.assign.announce.withdrawn":"“{cover}” goes back where it was: the change is withdrawn.","panel.assign.armed":"Tap the destination group for “{cover}”","panel.assign.drop_zone":"Take out of the profile — drop here","panel.assign.handle":"Move {cover} to another group, or reorder it","panel.assign.handle_hint":"Drag to assign or reorder, Enter to pick from a list","panel.assign.pending.all_own":"All values its own: nothing changes","panel.assign.pending.count":"{count} pending changes — nothing is written yet","panel.assign.pending.count_one":"1 pending change — nothing is written yet","panel.assign.pending.route":"{from} → {to}","panel.assign.pending.some_own":"Own values: those stay","panel.assign.target_none":"“No profile”","panel.assign.target_profile":"the profile “{profile}”","panel.banner.applying.body":"The covers are unavailable for a few seconds","panel.banner.applying.title":"The changes are being applied…","panel.banner.measuring.action.resume":"Resume the session","panel.banner.measuring.action.stop":"End it","panel.banner.measuring.body":"A guided calibration is using “{cover}”. Until the session ends, this panel only reads: nothing is written.","panel.banner.measuring.title":"Measurement in progress","panel.common.action.back":"Back","panel.common.action.cancel":"Cancel","panel.common.action.close":"Close","panel.common.action.configure":"Open Configure","panel.common.action.hide_all":"Hide the roll coefficients","panel.common.action.menu":"Open the Home Assistant menu","panel.common.action.retry":"Try again","panel.common.action.save":"Save","panel.common.action.show_all":"Show every value, roll coefficients included","panel.common.all_rooms":"All rooms","panel.common.gateway":"Gateway {gateway}","panel.common.loading":"Loading…","panel.common.not_yet":"This screen arrives in a later version. Until then “Configure” does everything it will do.","panel.common.opens_configure":"This opens the Configure dialog. The panel refreshes on its own when it closes.","panel.common.polling":"Live updates are not available on this version: the page refreshes on its own every 30 seconds.","panel.common.room_filter":"Filter by room","panel.common.search":"Search for a cover","panel.common.unit.centimetres":"cm","panel.common.unit.seconds":"s","panel.detail.action.assign":"Assign to a profile…","panel.detail.action.correct":"Correct…","panel.detail.action.correct_note":"If it stops in the wrong place: times only, times and rolls, or the thorough calibration only","panel.detail.action.edit":"Edit the values by hand","panel.detail.action.measure_again":"Measure again","panel.detail.action.measure_again_note":"Full basic calibration, in the dialog","panel.detail.action.remove":"Remove the measurement…","panel.detail.action.thorough":"Thorough calibration","panel.detail.action.thorough_note":"On top: readings at 25 and 75 % per direction, and a check","panel.detail.action.travel":"Set the curtain travel…","panel.detail.correct.intro":"The correction opens the Configure dialog on the path chosen. When it comes back, the panel refreshes on its own.","panel.detail.correct.thorough":"Thorough calibration only","panel.detail.correct.thorough_note":"Readings at 25 and 75 % per direction, and a check","panel.detail.correct.times":"Times only","panel.detail.correct.times_note":"One run per direction, the rolls stay","panel.detail.correct.times_rolls":"Times and rolls","panel.detail.correct.times_rolls_note":"Full basic calibration","panel.detail.destination.defaults":"the default values","panel.detail.destination.file":"the values of the configuration file","panel.detail.destination.profile":"the values inherited from the profile “{profile}”","panel.detail.edit.action.save":"Save the values","panel.detail.edit.empty":"empty = nothing to say","panel.detail.edit.inherits":"inherits {value}","panel.detail.edit.intro":"These values count for this cover alone and beat both the profile and the file. A field left empty is not a zero: it means “nothing to say about this one”, and the value goes back to coming from the profile or from the file. Emptying every field is the same as removing the measurement.","panel.detail.edit.title":"Edit the values by hand","panel.detail.level_basic":"basic calibration","panel.detail.level_thorough":"thorough calibration","panel.detail.measured_at":"Measured on {date}","panel.detail.named":"Cover “{cover}”","panel.detail.remove.action":"Remove the measurement","panel.detail.remove.body":"The measurements made on “{cover}” will be removed and cannot be recovered. The cover will go back to using {destination}.","panel.detail.remove.title":"Remove the measurement?","panel.detail.remove.travel_stays":"The curtain travel stays: somebody measured it with a tape.","panel.detail.source.default":"default value","panel.detail.source.file":"from the configuration file","panel.detail.source.own":"own value, measured on this cover","panel.detail.source.profile":"inherited from the profile “{profile}”","panel.detail.title":"Cover detail","panel.detail.unknown":"This gateway has no cover with that identifier.","panel.detail.values.intro":"What the cover is using right now, value by value, with where it comes from: a value of its own always wins; then the assigned profile, then the file, then the defaults.","panel.detail.values.title":"Values in use","panel.detail.verify_note":"{deviation} cm out at the check","panel.dialog.option.current":"current","panel.dialog.option.none":"No profile","panel.dialog.option.none_meta":"Values from the configuration file, or the defaults. The travel and the values of its own stay.","panel.dialog.option.profile":"Profile “{profile}”","panel.dialog.option.profile_meta":"{travel} cm · ascent {opening} s · descent {closing} s","panel.dialog.subtitle":"“{cover}” — the choice stays pending until it is confirmed.","panel.dialog.title":"Which profile?","panel.error.not_found":"The panel could not read this gateway.","panel.firstrun.action.measure":"Measure a cover","panel.firstrun.body":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.firstrun.how":"A profile is not written, it is measured. Pick one representative cover and measure it once, with the guided calibration: about three minutes. Similar covers can then follow it.","panel.firstrun.note":"This opens the Configure dialog: that is where the measuring happens. When it is done, the profile appears here.","panel.firstrun.title":"No profile yet","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.cover.follows":"follows “{profile}”","panel.overview.cover.from_file":"The configuration file assigns this profile: it is changed there, not here.","panel.overview.cover.origin_adjusted":"Adjusted","panel.overview.cover.origin_inherited":"Inherited","panel.overview.cover.profile_missing":"The profile “{profile}” is no longer defined: this cover is running on its own configuration.","panel.overview.cover.travel":"travel {travel} cm","panel.overview.cover.travel_needed":"travel to be entered","panel.overview.cover.travel_unknown":"travel not recorded","panel.overview.explanation":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.overview.group.count":"{count} covers","panel.overview.group.count_one":"1 cover","panel.overview.group.empty":"No cover in this group.","panel.overview.group.from_file":"Defined in the configuration file, and read-only from here.","panel.overview.group.measured_on":"Measured on {cover} · {date}","panel.overview.group.measured_on_gone":"Measured on a cover this gateway no longer has · {date}","panel.overview.group.missing":"This profile is not defined any more: the covers below have quietly fallen back to their own configuration.","panel.overview.group.no_profile":"No profile","panel.overview.group.no_profile_note":"Values from the configuration file, or the defaults. It is not a fault: a cover with measurements of its own sits perfectly well here.","panel.overview.group.open":"Open the profile card","panel.overview.group.profile":"Profile “{profile}”","panel.overview.group.provenance_missing":"Where it was measured is not recorded.","panel.overview.group.values":"Reference travel {travel} cm · ascent {opening} s · descent {closing} s · slats {slat} s","panel.overview.group.values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.no_basic_covers":"Every cover of this gateway reports its own position, so there is no travel model to calibrate and nothing for this panel to do.","panel.overview.no_results":"No cover matches this search.","panel.overview.summary":"Profiles: {profiles} · Basic covers: {covers}","panel.overview.title":"Profiles and covers","panel.profile.action.delete":"Delete the profile…","panel.profile.action.edit":"Edit the values…","panel.profile.action.rename":"Rename…","panel.profile.delete.action":"Delete the profile","panel.profile.delete.affects":"It affects these covers:","panel.profile.delete.body":"They will go back to the values of the configuration file, where those exist, or to the defaults. Their travels and their own values stay. The profile's measurements cannot be recovered.","panel.profile.delete.title":"Delete the profile “{profile}”?","panel.profile.edit.action.save":"Apply to {count} covers","panel.profile.edit.action.save_one":"Apply to 1 cover","panel.profile.edit.intro":"A change to the profile changes everything for the covers that inherit its values, and only the inherited values for the adjusted ones: the values of their own stay, key by key.","panel.profile.edit.reach":"The change reaches {target}","panel.profile.edit.reach_all":"every one of the {count} covers that follow the profile","panel.profile.edit.reach_one":"1 cover","panel.profile.followers.adjusted":"adjusted: own values for {keys}","panel.profile.followers.count":"{count} covers follow it","panel.profile.followers.count_one":"1 cover follows it","panel.profile.followers.inherited":"inherited","panel.profile.followers.measured":"measured: nothing inherited","panel.profile.followers.none":"No cover follows it.","panel.profile.from_file":"Profile of the configuration file: read-only here.","panel.profile.impact.invalid":"correct the fields to see the preview","panel.profile.impact.kept":"own values stay: {keys}","panel.profile.impact.no_change":"no change: all values are its own","panel.profile.impact.no_travel":"travel not recorded: it will use the profile's values as they are","panel.profile.impact.state_adjusted":"adjusted: only the inherited values change","panel.profile.impact.state_inherited":"inherited: everything changes","panel.profile.impact.state_measured":"measured","panel.profile.impact.title":"Impact preview","panel.profile.name":"Profile “{profile}”","panel.profile.provenance":"Measured on {cover} · {date}","panel.profile.provenance_missing":"Where it was measured is not recorded.","panel.profile.provenance_now_none":"now follows no profile","panel.profile.provenance_now_profile":"now follows “{profile}”","panel.profile.reference_travel":"Reference travel","panel.profile.rename.action":"Rename","panel.profile.rename.field":"New name of the profile","panel.profile.rename.rule":"Letters, digits and underscores only: no spaces, no accents — the name is also a key of the configuration file. The rename follows every cover that uses the profile.","panel.profile.rename.title":"Rename the profile","panel.profile.stored":"Stored profile","panel.profile.title":"Profile card","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.profile.values":"Values of the profile","panel.review.action.back":"Back to the overview","panel.review.action.confirm":"Confirm {count} assignments","panel.review.action.confirm_one":"Confirm 1 assignment","panel.review.action.missing_travel":"{count} travels missing","panel.review.action.missing_travel_one":"1 travel missing","panel.review.after":"After","panel.review.before":"Before","panel.review.intro":"The changes are written all at once. For each cover, this is what it will really use: the profile's values brought to its own travel.","panel.review.note.all_own":"It has values of its own for everything: nothing changes. The profile would only count for values removed later on.","panel.review.note.back_to_defaults":"The default values come back: the position in per cent will be a rough estimate. The travel and any value of its own stay.","panel.review.note.back_to_file":"The values of the configuration file come back. The travel and any value of its own stay.","panel.review.note.scaled":"Values of the profile “{profile}” (measured on {reference} cm) brought to a travel of {travel} cm.","panel.review.note.some_own":"It has some values of its own: those stay. Only the inherited values change.","panel.review.title":"Review and confirm","panel.review.travel.aria":"Curtain travel in centimetres","panel.review.travel.hint":"A profile is the measurement of one cover with a certain travel, and it is brought to the others in proportion. The travel of these is not known: measure the distance the bottom edge covers from fully closed to fully open, and write it in centimetres (decimals with a comma or with a point).","panel.review.travel.label":"Curtain travel","panel.review.travel.placeholder":"e.g. 145","panel.review.travel.required":"The travel is needed, in centimetres.","panel.review.travel.title":"How far does the curtain of these covers run?","panel.screen.completed":"Completed","panel.screen.motor":"Motor","panel.screen.new_text":"new text — not translated yet","panel.screen.not_in_this_version":"This step belongs to the guided calibration, which moves into the panel in a later version.","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.position":"Estimated position","panel.toast.action.undo":"Undo","panel.toast.assigned":"{count} assignments applied","panel.toast.assigned_one":"1 assignment applied","panel.toast.measure_removed":"Measurement removed: “{cover}” now uses {destination}.","panel.toast.order_saved":"The new order will be remembered.","panel.toast.profile_deleted":"Profile “{profile}” deleted: the covers go back to the file or to the defaults.","panel.toast.profile_renamed":"Renamed to “{profile}”: the rename follows every cover that uses it.","panel.toast.profile_saved":"Profile “{profile}” updated: {count} covers reached.","panel.toast.profile_saved_one":"Profile “{profile}” updated: 1 cover reached.","panel.toast.travel_saved":"The travel of “{cover}” is saved: the profile is brought to this measurement.","panel.toast.undone":"Changes undone: everything as it was.","panel.toast.values_saved":"The values of “{cover}” are saved: they beat the profile and the file."};var Ge=bt,xr=Object.keys(Ge);var zi="/myhome_static/",Di=/^!\[([^\]]*)\]\(([^)\s]+)\)$/;var he=r=>{let t=[];return r.split("**").forEach((i,n)=>{i&&t.push(n%2===1?a`<strong>${i}</strong>`:a`<span>${i}</span>`)}),t},Hi=r=>/^\s*[-*]\s+/.test(r),W=r=>{let t=(r||"").replace(/\r\n/g,`
`).split(/\n{2,}/),e=[];for(let i of t){let n=i.trim();if(!n)continue;let o=Di.exec(n);if(o){e.push(o[2].startsWith(zi)?a`<img class="md-image" src=${o[2]} alt=${o[1]} />`:a`<p>${he(o[1])}</p>`);continue}let s=n.split(`
`);if(s.every(Hi)){e.push(a`<ul>
          ${s.map(p=>a`<li>${he(p.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}e.push(a`<p>
        ${s.map((p,d)=>d===0?he(p):[a`<br />`,...he(p)])}
      </p>`)}return a`${e}`};var C=r=>r&&typeof r=="object"&&"code"in r?r:{code:"unknown_error",message:String(r)},yt=(r,t)=>r.sendMessagePromise({type:"myhome/calibration/overview",...t?{entry_id:t}:{}}),xt=(r,t)=>r.sendMessagePromise({type:"myhome/calibration/texts",language:t}),$t=(r,t,e)=>r.sendMessagePromise({type:"myhome/calibration/cover_detail",entry_id:t,cover_unique_id:e}),ue=(r,t,e,i)=>r.sendMessagePromise({type:"myhome/calibration/preview",entry_id:t,items:e,...i?{profile_values:i}:{}}),kt=(r,t,e)=>r.subscribeMessage(e,{type:"myhome/calibration/subscribe",...t?{entry_id:t}:{}}),ee=r=>C(r).code==="unknown_command",Rt=(r,t,e,i)=>r.sendMessagePromise({type:"myhome/calibration/assign",entry_id:t,assignments:e,...i?{order:i}:{}}),Et=(r,t,e,i)=>r.sendMessagePromise({type:"myhome/calibration/reorder",entry_id:t,order:e,...i!==void 0?{profile:i}:{}}),Pt=(r,t,e,i)=>r.sendMessagePromise({type:"myhome/calibration/set_travel",entry_id:t,cover_unique_id:e,height:i}),St=(r,t,e,i,n)=>r.sendMessagePromise({type:"myhome/calibration/cover_edit",entry_id:t,cover_unique_id:e,overrides:i,...n!==void 0?{height:n}:{}}),Ct=(r,t,e)=>r.sendMessagePromise({type:"myhome/calibration/cover_forget",entry_id:t,cover_unique_id:e}),Tt=(r,t,e,i,n)=>r.sendMessagePromise({type:"myhome/calibration/profile_edit",entry_id:t,name:e,values:i,reference_height:n}),At=(r,t,e,i)=>r.sendMessagePromise({type:"myhome/calibration/profile_rename",entry_id:t,name:e,new_name:i}),It=(r,t,e)=>r.sendMessagePromise({type:"myhome/calibration/profile_delete",entry_id:t,name:e}),Mt=(r,t,e)=>r.sendMessagePromise({type:"myhome/calibration/undo",entry_id:t,undo_token:e});var Ve=(r,t)=>{if(!t)return r;let e=r;for(let[i,n]of Object.entries(t))e=e.split(`{${i}}`).join(String(n));return e},b=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this.language="en";this.loaded=!1}async load(t,e){let i=await xt(t,e);this._texts=i.texts??{},this.language=i.language,this.loaded=!0,this._numbers.clear(),this._dates=null}t(t,e){let i=this._lookup(t);if(i!==null)return Ve(i,e);let n=Ge[t];return Ve(n??t,e)}md(t,e){return W(this.t(t,e))}refusal(t,e){let i=t?this._lookup(`exceptions.${t}.message`):null;return i!==null?Ve(i,e):this.t("panel.error.not_found")}origin(t,e){return this.t(`selector.calibration_origin.options.${t}`,{profile:e??""})}number(t,e){let i=this._numbers.get(e);return i||(i=new Intl.NumberFormat(this.language,{minimumFractionDigits:e,maximumFractionDigits:e}),this._numbers.set(e,i)),i.format(t)}date(t){let e=new Date(t);return Number.isNaN(e.getTime())?t:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(e))}_lookup(t){let e=this._texts;for(let i of t.split(".")){if(e===null||typeof e!="object")return null;e=e[i]}return typeof e=="string"?e:null}};var Lt=r=>typeof customElements<"u"&&customElements.get(r)!==void 0;var Ot=r=>{r.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var Ye=(r,t)=>{let e=me(r.unique_id,t);return e?e.to:r.profile??null},me=(r,t)=>t.find(e=>e.cover===r),zt=(r,t,e)=>{let i=r.filter(n=>n.cover!==t.unique_id);return e===(t.profile??null)?{pending:i,withdrawn:!0}:{pending:[...i,{cover:t.unique_id,to:e}],withdrawn:!1}},Dt=(r,t)=>{let e=new Map(r.covers.map(o=>[o.unique_id,o]));if(!t)return[...r.covers].sort((o,s)=>o.order_index-s.order_index);let i=new Set,n=[];for(let o of t){let s=e.get(o);s&&!i.has(o)&&(i.add(o),n.push(s))}for(let o of r.covers)i.has(o.unique_id)||n.push(o);return n},Ht=(r,t,e)=>{let i=r.filter(o=>o!==t),n=i.length;if(e.beforeId){let o=i.indexOf(e.beforeId);n=o<0?i.length:o}else if(e.afterId){let o=i.indexOf(e.afterId);n=o<0?i.length:o+1}return[...i.slice(0,n),t,...i.slice(n)]},Xe=(r,t)=>r.map(e=>{let i=t[e.cover],n=i===void 0?void 0:T(i);return{cover_unique_id:e.cover,profile:e.to,...n==null?{}:{height:n}}}),T=r=>{let t=r.trim().replace(",",".");if(!t)return null;let e=Number(t);return Number.isFinite(e)?e:null},Ni=20,Fi=500,te=r=>{if(r===void 0||r.trim()==="")return"missing_travel";let t=T(r);return t===null?"not_a_number":t<Ni||t>Fi?"out_of_range":null},Ze=r=>({cover_unique_id:r.unique_id,profile:r.profile_from_file?null:r.profile??null}),Nt=(r,t)=>t.to!==null&&r.height===null,A=["opening_time","closing_time","slat_time","opening_roll","closing_roll"],ie=["opening_time","closing_time","slat_time"],ve=["opening_roll","closing_roll"],x={opening_time:1,closing_time:1,slat_time:1,opening_roll:2,closing_roll:2};var I={opening_time:{min:1,max:600,decimals:1},closing_time:{min:1,max:600,decimals:1},slat_time:{min:0,max:60,decimals:1},opening_roll:{min:1,max:5,decimals:2},closing_roll:{min:1,max:5,decimals:2},height:{min:20,max:500,decimals:0},reference_height:{min:20,max:500,decimals:0}},ge={opening_time:"panel.common.unit.seconds",closing_time:"panel.common.unit.seconds",slat_time:"panel.common.unit.seconds",opening_roll:null,closing_roll:null,height:"panel.common.unit.centimetres",reference_height:"panel.common.unit.centimetres"},w=(r,t)=>{let e=(t??"").trim();if(e==="")return null;let i=T(e);if(i===null)return"not_a_number";let n=I[r];return n&&(i<n.min||i>n.max)?"out_of_range":null},M=r=>(r??"").trim()==="";var L="/config/integrations/integration/myhome";var Je="dialog-data-entry-flow",qi=()=>typeof customElements<"u"&&customElements.get(Je)!==void 0,Ft=r=>{history.pushState(null,"",r),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))},qt=r=>qi()?(r.source.dispatchEvent(new CustomEvent("show-dialog",{bubbles:!0,composed:!0,detail:{dialogTag:Je,dialogImport:()=>Promise.resolve(),dialogParams:{startFlowHandler:r.entryId,domain:"myhome"}}})),setTimeout(()=>{document.querySelector(Je)||(r.onLeaving(),Ft(L))},400),"waiting"):(r.onLeaving(),Ft(L),"page");var Ui={view:"overview",params:{},path:"/"},Ut=r=>{let t="/"+(r||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(t==="/")return Ui;let e=t.slice(1).split("/"),i=e.slice(1).join("/"),n=i;try{n=decodeURIComponent(i)}catch{}return e[0]==="cover"&&i?{view:"cover",params:{id:n},path:t}:e[0]==="profile"&&i?{view:"profile",params:{name:n},path:t}:e[0]==="calibrate"&&i?{view:"calibrate",params:{session:n},path:t}:{view:"unknown",params:{},path:t}};var fe=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(t){this._onChange=t,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(t){let e=t||"/";if(e===this._fromHost)return;let i=this.current.path;this._fromHost=e,this.current.path!==i&&this._emit()}get current(){let t=typeof location<"u"?location.hash:"";return t&&t.length>1?Ut(t.slice(1)):Ut(this._fromHost)}navigate(t){let e="#"+(t.startsWith("/")?t:"/"+t);location.hash!==e&&(location.hash=e)}_emit(){this._onChange(this.current)}};var re={for:null,answer:null,loading:!1,error:null,mode:"view",form:{},errors:{},preview:null,previewing:!1},ne={for:null,mode:"view",form:{},errors:{},newName:"",nameError:"",impact:null,impacting:!1},q=r=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:r,search:"",room:"",announce:"",pending:[],order:null,drag:null,armed:null,dialog:null,review:!1,heights:{},heightsForced:!1,showAll:!1,preview:null,previewing:!1,applying:!1,snack:null,writeError:null,detail:re,profile:ne}),we={pending:[],order:null,heights:{},heightsForced:!1,preview:null,previewing:!1,review:!1,writeError:null},_e=class{constructor(t){this._subscribers=new Set;this._state=q(t)}get state(){return this._state}subscribe(t){return this._subscribers.add(t),()=>this._subscribers.delete(t)}set(t){this._state={...this._state,...t};for(let e of this._subscribers)e(this._state)}setOverview(t){this.set({overview:t,entryId:t.entry_id,status:"ready",error:null})}setError(t){this.set({status:"error",error:t})}announce(t){this.set({announce:""}),this.set({announce:t})}};var $=u`:host{--myhome-text-on-primary: var(--text-primary-color, #ffffff);--myhome-snack-action: var(--snack-action-color, #ffc107);--myhome-primary: var(--primary-color, #03a9f4);--myhome-accent: var(--accent-color, #ff9800);--myhome-text: var(--primary-text-color, #212121);--myhome-text-soft: var(--secondary-text-color, #727272);--myhome-text-off: var(--disabled-text-color, #bdbdbd);--myhome-background: var(--primary-background-color, #fafafa);--myhome-background-soft: var(--secondary-background-color, #e5e5e5);--myhome-card: var(--card-background-color, #ffffff);--myhome-divider: var(--divider-color, rgba(0, 0, 0, .12));--myhome-error: var(--error-color, #db4437);--myhome-warning: var(--warning-color, #b26b00);--myhome-success: var(--success-color, #43a047);--myhome-info: var(--info-color, #039be5);--myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));--myhome-header-text: var(--app-header-text-color, #ffffff);--myhome-radius: var(--ha-card-border-radius, 12px);--myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, .14));--myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));--myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));--myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));--myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));--myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));--myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));--myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));--myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));--myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);display:block;min-height:100%;color:var(--myhome-text);background:var(--myhome-background)}*,*:before,*:after{box-sizing:border-box}:host * :focus-visible{outline:2px solid var(--myhome-primary);outline-offset:2px}@media(prefers-reduced-motion:reduce){:host *{animation-duration:.001ms!important;transition-duration:.001ms!important}}`,k=u`.card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}`,R=u`.cta{min-height:48px;padding:0 24px;border-radius:24px;border:none;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font:inherit;font-size:15px;font-weight:500;cursor:pointer}.cta.secondary{background:transparent;border:1px solid var(--myhome-primary);color:var(--myhome-primary)}.cta.text{background:transparent;border:none;color:var(--myhome-primary);padding:0 12px}.cta.destructive{background:var(--myhome-error-strong);color:var(--myhome-error)}.cta[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.cta.compact{min-height:44px;padding:0 18px;border-radius:22px;font-size:14px}`,z=u`.field{height:44px;border-radius:8px;border:1px solid var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text);padding:0 12px;font:inherit;font-size:14px}.field:disabled{color:var(--myhome-text-off)}`,be=u`.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0}`;var Wt=r=>a`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${r}</div>`,oe=r=>{requestAnimationFrame(()=>{let t=r();t&&t.focus()})};var ye=class{constructor(){this._root=null;this._onKey=t=>{if(t.key!=="Tab"||!this._root)return;let e=Bt(this._root);if(e.length===0){t.preventDefault(),this._root.focus();return}let i=e[0],n=e[e.length-1],o=this._root.getRootNode().activeElement;t.shiftKey&&(o===i||o===this._root)?(t.preventDefault(),n.focus()):!t.shiftKey&&o===n&&(t.preventDefault(),i.focus())}}hold(t){this.release(),this._root=t,t.addEventListener("keydown",this._onKey),oe(()=>Bt(t)[0]??t)}release(){this._root?.removeEventListener("keydown",this._onKey),this._root=null}},Bt=r=>Array.from(r.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter(t=>t.offsetParent!==null||t===r);var Kt=u`.measuring{max-width:1200px;margin:16px auto 0;padding:12px 16px;border-radius:var(--myhome-radius);background:var(--myhome-warning-pastel);display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.measuring strong{color:var(--myhome-warning);font-weight:500}.measuring .body{flex:1 1 320px;line-height:1.5}.measuring .links{display:flex;gap:16px}.measuring a{color:var(--myhome-primary);min-height:44px;display:inline-flex;align-items:center}`,jt=(r,t,e)=>a`<div class="measuring" role="status" aria-live="polite">
    <strong>${r.t("panel.banner.measuring.title")}</strong>
    <span class="body">${r.t("panel.banner.measuring.body",{cover:t})}</span>
    <span class="links">
      <a href=${e}>${r.t("panel.banner.measuring.action.resume")}</a>
      <a href=${e}>${r.t("panel.banner.measuring.action.stop")}</a>
    </span>
  </div>`;var xe=u`.strip{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translate(-50%);max-width:92vw;box-sizing:border-box;box-shadow:var(--myhome-shadow)}.drop-zone{z-index:45;padding:14px 28px;min-height:48px;display:flex;align-items:center;border-radius:24px;font-size:14px;font-weight:500;border:2px dashed var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text-soft)}.drop-zone.over{border:2px solid var(--myhome-primary);color:var(--myhome-primary)}.dark{background:var(--myhome-text);color:var(--myhome-background);border-radius:8px;font-size:14px}.armed{z-index:40;bottom:calc(84px + env(safe-area-inset-bottom,0px));padding:10px 16px;display:flex;gap:16px;align-items:center}.applying{z-index:70;padding:12px 20px}.applying .under{display:block;font-size:12px;opacity:.75;margin-top:2px}.snack{z-index:70;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:8px}.dark button{min-height:44px;padding:0 12px;border:none;background:transparent;color:var(--myhome-snack-action);font:inherit;font-weight:500;cursor:pointer}.pending-bar{z-index:30;background:var(--myhome-card);border:1px solid var(--myhome-divider);border-radius:28px;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.pending-bar .count{font-size:14px}.pending-bar .locked{font-size:13px;color:var(--myhome-warning);flex-basis:100%}.pending-bar button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.pending-bar .discard{padding:0 12px;background:transparent;color:var(--myhome-text-soft)}.pending-bar .review{padding:0 20px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.pending-bar button[disabled]{color:var(--myhome-text-off);background:var(--myhome-background-soft);cursor:default}@media(max-width:599px){.strip.pending-bar{left:8px;right:8px;transform:none;max-width:none;justify-content:space-between}.strip.pending-bar .count{flex-basis:100%}}`,Gt=(r,t)=>a`<div class="strip drop-zone ${t?"over":""}" data-group="none">
    ${r.t("panel.assign.drop_zone")}
  </div>`,Vt=(r,t,e)=>a`<div class="strip dark armed" role="status">
    <span>${r.t("panel.assign.armed",{cover:t})}</span>
    <button type="button" @click=${e}>${r.t("panel.common.action.cancel")}</button>
  </div>`,Yt=r=>{let{i18n:t}=r;return a`<div class="strip pending-bar">
    <span class="count"
      >${r.count===1?t.t("panel.assign.pending.count_one"):t.t("panel.assign.pending.count",{count:r.count})}</span
    >
    <button class="discard" type="button" @click=${r.onDiscard}>
      ${t.t("panel.assign.action.discard_all")}
    </button>
    <button
      class="review"
      type="button"
      ?disabled=${r.locked}
      title=${t.t("panel.assign.action.review_hint")}
      @click=${r.onReview}
    >
      ${t.t("panel.assign.action.review")}
    </button>
    ${r.locked?a`<span class="locked"
          >${t.t("panel.banner.measuring.body",{cover:r.lockedCover})}</span
        >`:l}
  </div>`},$e=r=>a`<div class="strip dark applying" role="status">
    ${r.t("panel.banner.applying.title")}
    <span class="under">${r.t("panel.banner.applying.body")}</span>
  </div>`,ke=(r,t,e)=>a`<div class="strip dark snack" role="status">
    <span>${t}</span>
    ${e?a`<button type="button" @click=${e}>
          ${r.t("panel.toast.action.undo")}
        </button>`:l}
  </div>`;var Xt=r=>{let t=new Map;for(let e of r.querySelectorAll("[data-row]")){let i=e.getBoundingClientRect();t.set(e.getAttribute("data-row")??"",{top:i.top,left:i.left})}return t},Zt=(r,t)=>{if(!Bi())for(let e of r.querySelectorAll("[data-row]")){let i=t.get(e.getAttribute("data-row")??"");if(!i)continue;let n=e.getBoundingClientRect(),o=i.left-n.left,s=i.top-n.top;if(Math.abs(o)<1&&Math.abs(s)<1)continue;e.style.transition="none",e.style.transform=`translate(${o}px, ${s}px)`,e.offsetHeight,e.style.transition="transform 220ms ease",e.style.transform="";let p=()=>{e.style.transition="",e.removeEventListener("transitionend",p)};e.addEventListener("transitionend",p)}},Bi=()=>typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches;var Re=class{constructor(t){this._start=null;this._longPress=null;this._pressedAt=null;this._ghost=null;this._target=null;this._scroll=null;this._edge=0;this._scroller=null;this._clearLongPressOnce=()=>this._clearLongPress();this._onPressMove=t=>{let e=this._pressedAt;e&&Math.hypot(t.clientX-e.x,t.clientY-e.y)<12||this._clearLongPress()};this._onMove=t=>{let e=this._start;if(!e)return;if(!e.live){if(Math.hypot(t.clientX-e.x,t.clientY-e.y)<6)return;e.live=!0,this._callbacks.onStart(e.cover)}this._moveGhost(t.clientX,t.clientY),this._autoScroll(t.clientX,t.clientY);let i=this._targetAt(t.clientX,t.clientY,e.cover);Wi(i,this._target)||(this._target=i,this._callbacks.onOver(i))};this._onUp=()=>this._finish(!0);this._onCancel=()=>this._finish(!1);this._callbacks=t}get dragging(){return this._start?.live?this._start.cover:null}press(t,e){if(!this._callbacks.blocked()){if(this._callbacks.narrow()){this._arm(t,e);return}e.preventDefault(),this._start={cover:t,x:e.clientX,y:e.clientY,live:!1},window.addEventListener("pointermove",this._onMove),window.addEventListener("pointerup",this._onUp),window.addEventListener("pointercancel",this._onCancel),window.addEventListener("blur",this._onCancel)}}arm(t,e){this._callbacks.blocked()||this._arm(t,e)}cancel(){if(this._start?.live){this._finish(!1);return}this._clear()}stop(){this._clear(),this._clearLongPress()}_arm(t,e){this._clearLongPress(),this._pressedAt=e?{x:e.clientX,y:e.clientY}:null,this._longPress=setTimeout(()=>{this._longPress=null,this._callbacks.onArm(t)},450),window.addEventListener("pointerup",this._clearLongPressOnce),window.addEventListener("pointermove",this._onPressMove),window.addEventListener("pointercancel",this._clearLongPressOnce),window.addEventListener("blur",this._clearLongPressOnce)}_clearLongPress(){this._longPress&&(clearTimeout(this._longPress),this._longPress=null),this._pressedAt=null,window.removeEventListener("pointerup",this._clearLongPressOnce),window.removeEventListener("pointermove",this._onPressMove),window.removeEventListener("pointercancel",this._clearLongPressOnce),window.removeEventListener("blur",this._clearLongPressOnce)}_finish(t){let e=this._start?.live??!1;this._clear(),e&&this._callbacks.onEnd(t)}_clear(){window.removeEventListener("pointermove",this._onMove),window.removeEventListener("pointerup",this._onUp),window.removeEventListener("pointercancel",this._onCancel),window.removeEventListener("blur",this._onCancel),this._start=null,this._target=null,this._stopScrolling(),this._ghost?.remove(),this._ghost=null}ghost(t,e){let i=document.createElement("div");i.className="drag-ghost",i.setAttribute("aria-hidden","true"),i.textContent=t,e.appendChild(i),this._ghost=i}_moveGhost(t,e){this._ghost&&(this._ghost.style.transform=`translate(${t+12}px, ${e+8}px)`)}_autoScroll(t,e){let i=this._callbacks.root().querySelector(".groups");if(!i||i.scrollWidth<=i.clientWidth){this._stopScrolling();return}let n=i.getBoundingClientRect(),o=t<n.left+64?-1:t>n.right-64?1:0;if(this._edge=o,this._scroller=i,o===0){this._stopScrolling();return}if(this._scroll===null){let s=()=>{this._edge===0||!this._scroller||(this._scroller.scrollLeft+=this._edge*14,this._scroll=requestAnimationFrame(s))};this._scroll=requestAnimationFrame(s)}}_stopScrolling(){this._edge=0,this._scroll!==null&&(cancelAnimationFrame(this._scroll),this._scroll=null)}_targetAt(t,e,i){let n=this._callbacks.root().elementFromPoint(t,e),o=n?.closest?.("[data-group]");if(!o)return null;let s=o.getAttribute("data-group")??"",p=n?.closest?.("[data-row]"),d=p?.getAttribute("data-row")??null;if(!p||!d||d===i)return{group:s,beforeId:null,afterId:null,end:!0};let c=p.getBoundingClientRect();return e<c.top+c.height/2?{group:s,beforeId:d,afterId:null,end:!1}:{group:s,beforeId:null,afterId:d,end:!1}}},Wi=(r,t)=>r===null||t===null?r===t:r.group===t.group&&r.beforeId===t.beforeId&&r.afterId===t.afterId;var Ee=u`.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.chip.measured{background:var(--myhome-primary-pastel);color:var(--myhome-text)}.chip.adjusted{background:var(--myhome-accent-pastel);color:var(--myhome-text)}.chip .dot{width:6px;height:6px;border-radius:3px;background:var(--myhome-accent);display:inline-block}`,Pe=(r,t,e,i)=>{let n=t==="measured"?"measured":t==="adjusted"?"adjusted":"neutral",o;return i&&t==="inherited"?o=r.t("panel.overview.cover.origin_inherited"):i&&t==="adjusted"?o=r.t("panel.overview.cover.origin_adjusted"):o=r.origin(t,e),a`<span class="chip ${n}"
    >${n==="adjusted"?a`<span class="dot" aria-hidden="true"></span>`:l}${o}</span
  >`};var Jt=u`.row{position:relative;display:flex;align-items:flex-start;gap:8px;padding:8px;border-radius:8px;min-height:48px;-webkit-user-select:none;-webkit-touch-callout:none}.row .divider{position:absolute;left:8px;right:8px;top:-1px;height:1px;background:var(--myhome-divider);opacity:.6;pointer-events:none}.row .insert-line{position:absolute;left:8px;right:8px;top:-2px;height:3px;border-radius:2px;background:var(--myhome-primary);pointer-events:none}.row .pending-outline{position:absolute;inset:0;border:2px dashed var(--myhome-primary);border-radius:8px;pointer-events:none}.row .source-veil{position:absolute;inset:0;background:var(--myhome-background-soft);opacity:.7;border-radius:8px;pointer-events:none}.row .handle{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);cursor:grab;font-size:18px;letter-spacing:2px;border-radius:8px;touch-action:none;-webkit-user-select:none;user-select:none}.row .handle[disabled]{cursor:default;color:var(--myhome-text-off)}@media(max-width:599px){.row .handle{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.row .handle:focus-visible{position:static;width:48px;height:48px;margin:0;overflow:visible;clip-path:none}}.row .main{flex:1 1 auto;min-width:0;text-align:left;border:none;background:transparent;color:inherit;font:inherit;cursor:pointer;padding:2px 0;border-radius:6px}.row .name{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:14.5px;line-height:1.35}.row .sub{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.row .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}.row .warn{display:block;font-size:12.5px;color:var(--myhome-warning);margin-top:4px}.route{display:inline-flex;align-items:center;gap:2px;font-size:12px;color:var(--myhome-primary);background:var(--myhome-primary-faint);border:1px dashed var(--myhome-primary);border-radius:10px;padding:2px 2px 2px 8px;max-width:100%}.route .text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.route .withdraw{width:48px;height:48px;margin:-14px -14px -14px 0;display:inline-flex;align-items:center;justify-content:center;border:none;background:transparent;color:inherit;font:inherit;font-size:14px;line-height:1;cursor:pointer;border-radius:24px}.row .note{display:block;font-size:12.5px;color:var(--myhome-info);margin-top:4px}`,Ki=(r,t,e)=>{let i=t.height!==null?r.t("panel.overview.cover.travel",{travel:r.number(t.height,0)}):e?r.t("panel.overview.cover.travel_needed"):r.t("panel.overview.cover.travel_unknown");return t.area?`${t.area} · ${i}`:i},ji=(r,t)=>t.has_own.length===0?"":A.every(e=>t.has_own.includes(e))?r.t("panel.assign.pending.all_own"):r.t("panel.assign.pending.some_own"),Qt=(r,t)=>{let{i18n:e,pending:i}=t,n=!!i&&i.to!==null&&r.height===null,o=i?ji(e,r):"";return a`<div class="row" data-row=${r.unique_id}>
    ${t.insertBefore?a`<div class="insert-line" aria-hidden="true"></div>`:t.first?l:a`<div class="divider" aria-hidden="true"></div>`}
    ${i?a`<div class="pending-outline" aria-hidden="true"></div>`:l}
    ${t.dragging?a`<div class="source-veil" aria-hidden="true"></div>`:l}
    <button
      class="handle"
      type="button"
      ?disabled=${t.locked}
      aria-label=${e.t("panel.assign.handle",{cover:r.name})}
      title=${t.locked?e.t("panel.banner.measuring.title"):e.t("panel.assign.handle_hint")}
      @pointerdown=${s=>t.onGrab(r,s)}
      @click=${s=>s.stopPropagation()}
      @keydown=${s=>{(s.key==="Enter"||s.key===" ")&&(s.preventDefault(),t.locked||t.onPick(r))}}
    >
      ⠿
    </button>
    <button
      class="main"
      type="button"
      title=${r.name}
      @click=${()=>t.onOpen(r)}
      @pointerdown=${s=>t.onRowPress(r,s)}
    >
      <span class="name">${r.name}</span>
      <span class="sub">${Ki(e,r,n)}</span>
      <span class="chips">
        ${Pe(e,r.origin,r.profile,t.short)}
        ${i?a`<span class="route">
              <span class="text">${t.route}</span>
              <span
                class="withdraw"
                role="button"
                tabindex="0"
                aria-label=${e.t("panel.assign.action.withdraw")}
                title=${e.t("panel.assign.action.withdraw")}
                @click=${s=>{s.stopPropagation(),t.onWithdraw(r)}}
                @keydown=${s=>{(s.key==="Enter"||s.key===" ")&&(s.preventDefault(),s.stopPropagation(),t.onWithdraw(r))}}
                >✕</span
              >
            </span>`:l}
      </span>
      ${o?a`<span class="note">${o}</span>`:l}
      ${r.profile_missing?a`<span class="warn"
            >${e.t("panel.overview.cover.profile_missing",{profile:r.profile??""})}</span
          >`:l}
      ${r.profile_from_file&&!r.profile_missing?a`<span class="sub">${e.t("panel.overview.cover.from_file")}</span>`:l}
    </button>
  </div>`};var ei=u`.backdrop{position:fixed;inset:0;background:#0006;z-index:60}.dialog{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(440px,92vw);max-height:80vh;overflow:auto;background:var(--myhome-card);color:var(--myhome-text);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);z-index:61;padding:20px;box-sizing:border-box}.dialog h2{margin:0 0 4px;font-size:18px;font-weight:500}.dialog .subtitle{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft)}.dialog .options{display:flex;flex-direction:column;gap:8px}.dialog .option{text-align:left;border-radius:8px;font:inherit;padding:12px;min-height:48px;cursor:pointer;border:1px solid var(--myhome-divider);background:transparent;color:inherit}.dialog .option.current{border-color:var(--myhome-primary);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.dialog .option .line{display:flex;align-items:baseline;gap:8px}.dialog .option .title{font-weight:500;flex:1}.dialog .option .tag{font-size:12.5px;color:var(--myhome-primary)}.dialog .option .meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.dialog .foot{display:flex;justify-content:flex-end;margin-top:12px}.dialog .foot button{min-height:44px;padding:0 16px;border:none;background:transparent;color:var(--myhome-text-soft);font:inherit;font-size:14px;cursor:pointer}`,Gi=(r,t)=>t.missing||t.values.opening_time===void 0?r.t("panel.overview.group.values_unknown"):r.t("panel.dialog.option.profile_meta",{travel:t.reference_height===null?"?":r.number(t.reference_height,0),opening:r.number(t.values.opening_time,1),closing:r.number(t.values.closing_time,1)}),ti=r=>{let{i18n:t}=r,e=(i,n,o)=>a`<button
    class="option ${r.current===i?"current":""}"
    type="button"
    aria-current=${r.current===i?"true":l}
    @click=${()=>r.onPick(i)}
  >
    <span class="line"
      ><span class="title">${n}</span
      >${r.current===i?a`<span class="tag">${t.t("panel.dialog.option.current")}</span>`:l}</span
    >
    <span class="meta">${o}</span>
  </button>`;return a`
    <div class="backdrop" aria-hidden="true" @click=${r.onClose}></div>
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      data-focus-root
    >
      <h2 id="dialog-title">${t.t("panel.dialog.title")}</h2>
      <p class="subtitle">
        ${t.t("panel.dialog.subtitle",{cover:r.cover.name})}
      </p>
      <div class="options">
        ${r.profiles.map(i=>e(i.name,t.t("panel.dialog.option.profile",{profile:i.name}),Gi(t,i)))}
        ${e(null,t.t("panel.dialog.option.none"),t.t("panel.dialog.option.none_meta"))}
      </div>
      <div class="foot">
        <button type="button" @click=${r.onClose}>
          ${t.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `};var ii=u`.groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(300px,1fr);gap:16px;align-items:start;overflow-x:auto;padding-bottom:8px;overscroll-behavior-x:contain}}.group{position:relative;background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.group-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider)}.group-head .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.group-head h2{margin:0;font-size:17px;font-weight:500;flex:1 1 auto;min-width:0}.group-head h2 button{border:none;background:transparent;color:var(--myhome-primary);font:inherit;cursor:pointer;padding:0;min-height:28px;text-align:left}.group-head .count{color:var(--myhome-text-soft);font-size:13px}.group-head .meta{margin:6px 0 0;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}.group-head .meta.second{margin-top:4px}.group-head .meta.warn{color:var(--myhome-warning)}.group-body{display:flex;flex-direction:column;padding:8px;gap:2px;min-height:56px}.group-body .empty{margin:8px;font-size:13px;color:var(--myhome-text-soft)}.group-body .insert-end{margin:0 8px;height:3px;border-radius:2px;background:var(--myhome-primary);pointer-events:none}.group .over,.group .armed-target{position:absolute;inset:0;border-radius:var(--myhome-radius);pointer-events:none}.group .over{border:2px solid var(--myhome-primary)}.group .armed-target{border:2px dashed var(--myhome-primary)}.group.collapsed .group-head{border-bottom:none;min-height:48px;cursor:pointer}`,Qe=r=>r===null?"none":`profile:${r}`,ri=r=>r==="none"?null:r.slice(8),ni=(r,t)=>{let{i18n:e}=t,i=r.covers.length===1?e.t("panel.overview.group.count_one"):e.t("panel.overview.group.count",{count:r.covers.length}),n=t.collapsed;return a`<section
    class="group ${n?"collapsed":""}"
    data-group=${Qe(r.key)}
    aria-labelledby=${r.id}
  >
    <div
      class="group-head"
      @click=${()=>{n&&t.onTarget(r.key)}}
    >
      <div class="line">
        <h2 id=${r.id}>
          ${r.key===null?r.title:a`<button
                type="button"
                title=${n?e.t("panel.assign.armed",{cover:""}):e.t("panel.overview.group.open")}
                @click=${o=>{if(o.stopPropagation(),n){t.onTarget(r.key);return}t.onOpenProfile(r.key)}}
              >
                ${r.title}
              </button>`}
        </h2>
        <span class="count">${i}</span>
      </div>
      ${r.values&&!n?a`<p class="meta">${r.values}</p>`:l}
      ${n?l:r.warning?a`<p class="meta second warn">${r.warning}</p>`:r.provenance?a`<p class="meta second">${r.provenance}</p>`:l}
    </div>
    ${n?l:a`<div class="group-body">
          ${r.covers.map((o,s)=>Qt(o,{i18n:e,short:o.profile===r.key,first:s===0,pending:t.pending.find(p=>p.cover===o.unique_id),route:t.route(o),locked:t.locked,insertBefore:t.insertBefore===o.unique_id,dragging:t.dragging===o.unique_id,onOpen:t.onOpenCover,onGrab:t.onGrab,onRowPress:t.onRowPress,onPick:t.onPick,onWithdraw:t.onWithdraw}))}
          ${t.insertEnd?a`<div class="insert-end" aria-hidden="true"></div>`:l}
          ${r.covers.length===0?a`<p class="empty">${e.t("panel.overview.group.empty")}</p>`:l}
        </div>`}
    ${t.over?a`<div class="over" aria-hidden="true"></div>`:l}
    ${n?a`<div class="armed-target" aria-hidden="true"></div>`:l}
  </section>`};var si=u`.sheet-backdrop{position:fixed;inset:0;background:#0006;z-index:50}.sheet{position:fixed;left:0;right:0;bottom:0;max-height:86vh;background:var(--myhome-card);color:var(--myhome-text);z-index:51;border-radius:16px 16px 0 0;box-shadow:var(--myhome-shadow);display:flex;flex-direction:column}@media(min-width:600px){.sheet{inset:0 0 0 auto;width:min(480px,100vw);max-height:none;border-radius:0}}.sheet .head{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--myhome-divider)}.sheet .head h2{margin:0;font-size:18px;font-weight:500;flex:1}.sheet .head button{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);font-size:20px;cursor:pointer;border-radius:24px}.sheet .body{flex:1;overflow:auto;padding:16px}.sheet .intro{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .travel-note{background:var(--myhome-info-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}.sheet .travel-note strong{font-weight:500;display:block;margin-bottom:4px}.sheet .item{border:1px solid var(--myhome-divider);border-radius:8px;padding:12px;margin:0 0 12px}.sheet .item .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.sheet .item .name{font-weight:500;flex:1 1 auto;min-width:0}.sheet .item .route{font-size:13px;color:var(--myhome-text-soft)}.sheet label.travel{display:flex;align-items:center;gap:8px;margin:10px 0 2px;font-size:13.5px}.sheet label.travel .what{flex:1}.sheet label.travel input{width:96px;height:44px;border-radius:8px;border:1px solid var(--myhome-divider);background:var(--myhome-card);color:inherit;padding:0 10px;font:inherit;font-size:14px;text-align:right}.sheet label.travel input[aria-invalid=true]{border-color:var(--myhome-error)}.sheet .field-error{margin:2px 0 0;font-size:12.5px;color:var(--myhome-error);text-align:right}.sheet table{width:100%;border-collapse:collapse;margin:10px 0 0;font-size:13.5px}.sheet th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}.sheet th.what{text-align:left}.sheet th.after{font-weight:500;color:var(--myhome-text)}.sheet td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}.sheet td.what{text-align:left;color:var(--myhome-text-soft)}.sheet td.after{font-weight:500}.sheet .note{margin:10px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .problem{margin:10px 0 0;font-size:12.5px;color:var(--myhome-error);line-height:1.5}.sheet .show-all{border:none;background:transparent;color:var(--myhome-primary);font:inherit;font-size:13.5px;cursor:pointer;padding:4px 0;min-height:44px}.sheet .refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 12px;font-size:13.5px;line-height:1.5}.sheet .foot{padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));border-top:1px solid var(--myhome-divider);display:flex;gap:12px;justify-content:flex-end}.sheet .foot button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.sheet .foot .back{padding:0 16px;background:transparent;color:var(--myhome-text-soft)}.sheet .foot .confirm{padding:0 24px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.sheet .foot .confirm[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}`,Vi=(r,t,e,i,n)=>{if(A.every(s=>t.has_own.includes(s)))return r.t("panel.review.note.all_own");if(t.has_own.length>0)return r.t("panel.review.note.some_own");if(e.to===null)return i?.origin==="from_the_file"?r.t("panel.review.note.back_to_file"):r.t("panel.review.note.back_to_defaults");let o=n.get(e.to);return!i||i.height===null||!o||o.reference_height===null?"":r.t("panel.review.note.scaled",{profile:e.to,reference:r.number(o.reference_height,0),travel:r.number(i.height,0)})},oi=(r,t,e,i)=>r.refusal(e,{cover:t.name,covers:t.name,count:1,profile:i.to??"",key:r.t("panel.review.travel.label"),min:20,max:500}),ai=r=>{let{i18n:t}=r,e=new Map((r.preview??[]).map(p=>[p.cover_unique_id,p])),i=r.pending.map(p=>({change:p,cover:r.covers.get(p.cover)})).filter(p=>p.cover!==void 0),n=i.filter(({change:p,cover:d})=>p.to!==null&&d.height===null&&te(r.heights[p.cover])!==null).length,o=r.showAll?[...ie,...ve]:ie,s=p=>t.t(`options.step.calibration_edit.data.${p}`);return a`
    <!--
      While the batch is in the air every way out is inert, the backdrop and the ✕
      included: Escape is already guarded, and a panel that could be dismissed by a stray
      click on the dark half would take the refusal - and the pending changes it is about
      to show again - off the screen with it.
    -->
    <div
      class="sheet-backdrop"
      aria-hidden="true"
      @click=${()=>{r.applying||r.onClose()}}
    ></div>
    <aside
      class="sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-title"
      data-focus-root
    >
      <div class="head">
        <h2 id="review-title">${t.t("panel.review.title")}</h2>
        <button
          type="button"
          aria-label=${t.t("panel.common.action.close")}
          ?disabled=${r.applying}
          @click=${r.onClose}
        >
          ✕
        </button>
      </div>
      <div class="body">
        <p class="intro">${t.t("panel.review.intro")}</p>
        ${r.refusal?a`<div class="refusal" role="alert">${r.refusal}</div>`:l}
        ${n>0?a`<div class="travel-note">
              <strong>${t.t("panel.review.travel.title")}</strong>
              ${t.t("panel.review.travel.hint")}
            </div>`:l}
        ${i.map(({change:p,cover:d})=>{let c=e.get(p.cover),m=r.heights[p.cover],h=p.to!==null&&d.height===null,v=h?te(m):null,f=v!==null&&(r.forced||(m??"")!==""),D=c&&c.problem===null?o.filter(_=>c.values[_]!==void 0&&d.values[_]!==void 0):[];return a`<section class="item">
            <div class="line">
              <span class="name">${d.name}</span>
              <span class="route">${r.route(d)}</span>
            </div>
            ${h?a`<label class="travel">
                    <span class="what">${t.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${m??""}
                      ?disabled=${r.applying}
                      aria-label=${t.t("panel.review.travel.aria")}
                      aria-invalid=${f?"true":"false"}
                      placeholder=${t.t("panel.review.travel.placeholder")}
                      @input=${_=>r.onHeight(p.cover,_.target.value)}
                    />
                    <span>${t.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${f?a`<p class="field-error">
                        ${v==="missing_travel"?t.t("panel.review.travel.required"):oi(t,d,v,p)}
                      </p>`:l}`:l}
            ${c&&c.problem!==null&&c.problem!=="missing_travel"?a`<p class="problem">
                  ${oi(t,d,c.problem,p)}
                </p>`:l}
            ${D.length>0?a`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${t.t("panel.review.before")}</th>
                      <th class="after">${t.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${D.map(_=>a`<tr>
                        <td class="what">${s(_)}</td>
                        <td>${t.number(d.values[_],x[_]??1)}</td>
                        <td class="after">
                          ${t.number(c.values[_],x[_]??1)}
                        </td>
                      </tr>`)}
                  </tbody>
                </table>`:l}
            ${(()=>{let _=Vi(t,d,p,c,r.profiles);return _?a`<p class="note">${_}</p>`:l})()}
          </section>`})}
        <button class="show-all" type="button" @click=${r.onToggleShowAll}>
          ${r.showAll?t.t("panel.common.action.hide_all"):t.t("panel.common.action.show_all")}
        </button>
      </div>
      <div class="foot">
        <button class="back" type="button" ?disabled=${r.applying} @click=${r.onClose}>
          ${t.t("panel.review.action.back")}
        </button>
        <button
          class="confirm"
          type="button"
          ?disabled=${r.applying||r.forced&&n>0}
          @click=${r.onConfirm}
        >
          ${r.applying?t.t("panel.banner.applying.title"):n>0?n===1?t.t("panel.review.action.missing_travel_one"):t.t("panel.review.action.missing_travel",{count:n}):i.length===1?t.t("panel.review.action.confirm_one"):t.t("panel.review.action.confirm",{count:i.length})}
        </button>
      </div>
    </aside>
  `};var Se=class extends g{constructor(){super();this._trap=new ye;this._returnTo=null;this._returnToRow=null;this._onKey=e=>{if(e.key==="Escape"){if(this.state.drag){this._drag.cancel();return}if(this.state.armed){this.actions.arm(null);return}if(this.state.dialog){this.actions.dialog(null);return}this.state.review&&!this.state.applying&&this.actions.review(!1)}};this._flip=null;this._route=e=>{let i=me(e.unique_id,this.state.pending);return i?this.i18n.t("panel.assign.pending.route",{from:this._groupName(e.profile??null),to:this._groupName(i.to)}):""};this._onGrab=(e,i)=>{this._drag.press(e.unique_id,i)};this._onRowPress=(e,i)=>{this._narrow&&!this._locked&&this._drag.arm(e.unique_id,i)};this.i18n=new b,this.state=q({view:"overview",params:{},path:"/"}),this.actions={},this._drag=new Re({root:()=>this.renderRoot,blocked:()=>this._locked,narrow:()=>this._narrow,onArm:e=>{let i=this._cover(e);i&&this.actions.arm(i)},onStart:e=>{let i=this._cover(e);i&&(this._drag.ghost(i.name,this.renderRoot),this.actions.drag(i))},onOver:e=>this.actions.over(e),onEnd:e=>this._endDrag(e)})}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[$,k,R,z,Ee,Jt,ii,xe,ei,si,u`:host{display:block;background:transparent}.intro{margin:8px 0 4px;max-width:72ch}.intro p{margin:0 0 8px;line-height:1.55}.counts{margin:0 0 16px;color:var(--myhome-text-soft)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.controls .search{flex:1 1 220px;max-width:340px}.controls .spacer{flex:1 1 auto}.select-wrap{position:relative;display:inline-flex}.select-wrap:after{content:"";position:absolute;right:13px;top:50%;width:7px;height:7px;border-right:1.6px solid var(--myhome-text-soft);border-bottom:1.6px solid var(--myhome-text-soft);border-radius:1px;transform:translateY(-70%) rotate(45deg);pointer-events:none}select.field{appearance:none;padding-right:36px}a.cta{display:inline-flex;align-items:center;text-decoration:none}.welcome{max-width:640px;margin:48px auto;padding:32px}.welcome h2{margin:0 0 12px;font-size:22px;font-weight:500}.welcome p{margin:0 0 8px;line-height:1.55}.welcome .soft{color:var(--myhome-text-soft);margin-bottom:24px}.welcome .after{margin:12px 0 0;font-size:13px;color:var(--myhome-text-soft)}.notice{padding:16px;margin:16px 0;font-size:14px;line-height:1.55}.notice .actions{margin-top:12px}.groups{margin-bottom:96px}.drag-ghost{position:fixed;left:0;top:0;z-index:80;pointer-events:none;background:var(--myhome-card);color:var(--myhome-text);border:1px solid var(--myhome-primary);border-radius:8px;box-shadow:var(--myhome-shadow);padding:10px 14px;font-size:14px;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}`]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._drag.stop(),this._trap.release()}updated(e){if(e.has("state")){let i=e.get("state");if(this._manageFocus(i),this._flip){let n=this._flip;this._flip=null,requestAnimationFrame(()=>Zt(this.renderRoot,n))}}}_beforeMove(){this._flip=Xt(this.renderRoot)}_manageFocus(e){let i=this.state.dialog!==null||this.state.review,n=(e?.dialog??null)!==null||(e?.review??!1);if(i&&!n){let o=this._activeElement();this._returnTo=o,this._returnToRow=o?.closest("[data-row]")?.getAttribute("data-row")??null,requestAnimationFrame(()=>{let s=this.renderRoot.querySelector("[data-focus-root]");s&&this._trap.hold(s)});return}if(!i&&n){this._trap.release();let o=this._returnTo,s=this._returnToRow;this._returnTo=null,this._returnToRow=null,requestAnimationFrame(()=>{((s?this.renderRoot.querySelector(`[data-row="${CSS.escape(s)}"] .handle`):null)??(o?.isConnected?o:null))?.focus()})}}_activeElement(){let e=this.renderRoot.activeElement;return e instanceof HTMLElement?e:null}get _overview(){return this.state.overview}get _locked(){return this._overview?.measuring!=null||this.state.applying}get _narrow(){return typeof matchMedia=="function"&&matchMedia("(max-width: 599px)").matches}_cover(e){return this._overview?.covers.find(i=>i.unique_id===e)}get _covers(){let e=this._overview;return e?Dt(e,this.state.order):[]}get _rooms(){let e=new Set;for(let i of this._overview?.covers??[])i.area&&e.add(i.area);return Array.from(e).sort((i,n)=>i.localeCompare(n,this.i18n.language))}_matches(e){let i=this.state.search.trim().toLowerCase();return i&&!e.name.toLowerCase().includes(i)?!1:!this.state.room||e.area===this.state.room}_groupName(e){return e===null?this.i18n.t("panel.overview.group.no_profile"):this.i18n.t("panel.overview.group.profile",{profile:e})}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group.values_unknown"):this.i18n.t("panel.overview.group.values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),opening:this.i18n.number(e.values.opening_time,1),closing:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml")return this.i18n.t("panel.overview.group.from_file");if(!e.measured_on)return this.i18n.t("panel.overview.group.provenance_missing");let i=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.group.measured_on_gone",{date:i});let n=this.i18n.t("panel.overview.group.measured_on",{cover:e.measured_on_name,date:i}),o=(this._overview?.covers??[]).find(s=>s.unique_id===e.measured_on);if(o&&o.profile!==e.name){let s=o.profile??this.i18n.t("panel.overview.group.no_profile");n+=` · ${this.i18n.t("panel.profile.provenance_now_profile",{profile:s})}`}return n}get _groups(){let e=this._overview;if(!e)return[];let i=this._covers,n=s=>i.filter(p=>Ye(p,this.state.pending)===s&&this._matches(p)),o=e.profiles.map((s,p)=>({key:s.name,id:`group-${p}`,title:this.i18n.t("panel.overview.group.profile",{profile:s.name}),values:this._valuesLine(s),provenance:this._provenanceLine(s),warning:s.missing?this.i18n.t("panel.overview.group.missing"):"",covers:n(s.name)}));return o.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group.no_profile"),values:this.i18n.t("panel.overview.group.no_profile_note"),provenance:"",warning:"",covers:n(null)}),o}_endDrag(e){let i=this.state,n=i.drag,o=n?.insert??null,s=n?.over??null,p=n?this._cover(n.cover):void 0;if(this.actions.drag(null),!e||!p||s===null){n&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));return}let d=ri(s),c=this._covers.map(f=>f.unique_id),m=Ht(c,p.unique_id,o??{beforeId:null,afterId:null});this._beforeMove();let h=me(p.unique_id,i.pending),v=h?h.to:p.profile??null;if(d!==v){this.actions.setOrder(m),this.actions.assign(p,d);return}if(i.pending.length>0){this.actions.setOrder(m),this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));return}this.actions.reorder(m)}_renderControls(){return a`<div class="controls">
      <input
        class="field search"
        type="search"
        .value=${this.state.search}
        placeholder=${this.i18n.t("panel.common.search")}
        aria-label=${this.i18n.t("panel.common.search")}
        @input=${e=>this.actions.search(e.target.value)}
      />
      <span class="select-wrap">
        <select
          class="field"
          aria-label=${this.i18n.t("panel.common.room_filter")}
          .value=${this.state.room}
          @change=${e=>this.actions.room(e.target.value)}
        >
          <option value="">${this.i18n.t("panel.common.all_rooms")}</option>
          ${this._rooms.map(e=>a`<option value=${e}>${e}</option>`)}
        </select>
      </span>
      <span class="spacer"></span>
      <a class="cta secondary compact" href=${L} title=${this.i18n.t("panel.firstrun.note")}
        >${this.i18n.t("panel.firstrun.action.measure")}</a
      >
    </div>`}_renderFirstRun(){return a`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <a class="cta" href=${L}>${this.i18n.t("panel.firstrun.action.measure")}</a>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`}_renderStrips(){let e=this.state;if(e.drag)return Gt(this.i18n,e.drag.over==="none");if(e.armed){let i=this._cover(e.armed);return Vt(this.i18n,i?.name??"",()=>this.actions.arm(null))}return e.applying?$e(this.i18n):e.snack?ke(this.i18n,e.snack.message,e.snack.undoToken?()=>this.actions.undo():null):e.pending.length>0&&!e.review?Yt({i18n:this.i18n,count:e.pending.length,locked:this._locked,lockedCover:this._overview?.measuring?.name??"",onDiscard:()=>{this._beforeMove(),this.actions.discardAll()},onReview:()=>this.actions.review(!0)}):l}_renderDialog(){let e=this.state.dialog?this._cover(this.state.dialog):void 0;return e?ti({i18n:this.i18n,cover:e,profiles:this._overview?.profiles??[],current:Ye(e,this.state.pending),onPick:i=>{this._beforeMove(),this.actions.assign(e,i)},onClose:()=>this.actions.dialog(null)}):l}_renderReview(){let e=this._overview;return!this.state.review||!e?l:ai({i18n:this.i18n,pending:this.state.pending,covers:new Map(e.covers.map(i=>[i.unique_id,i])),profiles:new Map(e.profiles.map(i=>[i.name,i])),preview:this.state.preview,heights:this.state.heights,forced:this.state.heightsForced,showAll:this.state.showAll,applying:this.state.applying,refusal:this.state.writeError?this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{}):"",route:this._route,onHeight:(i,n)=>this.actions.height(i,n),onToggleShowAll:()=>this.actions.toggleShowAll(),onConfirm:()=>this.actions.confirm(),onClose:()=>this.actions.review(!1)})}render(){let e=this._overview;if(!e)return a`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return a`<div class="card notice">
        ${W(this.i18n.t("panel.overview.no_basic_covers"))}
      </div>`;if(e.profiles.length===0)return this._renderFirstRun();let i=this._groups,n=i.reduce((p,d)=>p+d.covers.length,0),o=this.state.search.trim()!==""||this.state.room!=="",s=this.state.drag;return a`
      <div class="intro">${this.i18n.md("panel.overview.explanation")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.summary",{profiles:e.profiles.length,covers:e.covers.length})}
      </p>
      ${this._renderControls()}
      ${n===0&&o?a`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${()=>this.actions.clearFilters()}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`:a`<div class="groups">
            ${i.map(p=>{let d=Qe(p.key),c=s?.insert??null,m=c!==null&&c.group===d;return ni(p,{i18n:this.i18n,pending:this.state.pending,route:this._route,locked:this._locked,collapsed:this.state.armed!==null,over:s?.over===d,insertBefore:m?c.beforeId:null,insertEnd:m?c.end||c.afterId===p.covers.at(-1)?.unique_id:!1,dragging:s?.cover??null,onOpenProfile:h=>this.actions.openProfile(h),onOpenCover:h=>this.actions.openCover(h.unique_id),onGrab:this._onGrab,onRowPress:this._onRowPress,onPick:h=>this.actions.dialog(h),onWithdraw:h=>{this._beforeMove(),this.actions.withdraw(h)},onTarget:h=>{let v=this.state.armed?this._cover(this.state.armed):void 0;v&&(this._beforeMove(),this.actions.assign(v,h))}})})}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",Se);var Ce=u`:host{display:block}.card{padding:16px;margin:0 0 16px;max-width:720px}h2{margin:0 0 4px;font-size:16px;font-weight:500}h2:focus-visible{outline:2px solid var(--myhome-primary);outline-offset:4px}.sub{margin:0;font-size:13px;color:var(--myhome-text-soft)}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}.intro{margin:0 0 12px;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}.rows{display:flex;flex-direction:column}.row{display:flex;align-items:baseline;gap:8px;padding:8px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.row .what{flex:1 1 150px;color:var(--myhome-text-soft)}.row .value{font-variant-numeric:tabular-nums;font-weight:500}.row .from{flex-basis:100%;font-size:12px;color:var(--myhome-text-soft);text-align:right}.row .instead{font-size:12px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}h3{margin:16px 0 4px;font-size:14px;font-weight:500}.actions{display:flex;flex-direction:column;gap:8px}.wide{min-height:48px;border:none;border-radius:8px;background:var(--myhome-primary-faint);color:var(--myhome-primary);font:inherit;font-size:14px;cursor:pointer;text-align:left;padding:10px 14px;display:block;width:100%}.wide.destructive{background:var(--myhome-error-strong);color:var(--myhome-error)}.wide[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.wide .note{display:block;color:var(--myhome-text-soft);font-size:12.5px;margin-top:2px}.warn{background:var(--myhome-warning-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13px;line-height:1.5}.warn strong{font-weight:500;display:block;margin-bottom:4px}.danger{background:var(--myhome-error-pastel);border-radius:8px;padding:16px;font-size:14px;line-height:1.55}.danger strong{font-weight:500}.danger p{margin:8px 0 0}.danger ul{margin:4px 0 0;padding:0 0 0 20px;line-height:1.7}.danger .soft{color:var(--myhome-text-soft);font-size:13px}.fields{display:flex;flex-direction:column;gap:10px}label.field-row{display:flex;align-items:center;gap:8px;font-size:13.5px}label.field-row .what{flex:1}label.field-row input{width:110px;text-align:right}label.field-row .unit{color:var(--myhome-text-soft);width:24px}.field[aria-invalid=true]{border-color:var(--myhome-error)}.field-error{margin:2px 26px 0 0;font-size:12.5px;color:var(--myhome-error);text-align:right}.foot{display:flex;gap:12px;justify-content:flex-end;margin-top:16px}table{width:100%;border-collapse:collapse;margin:16px 0 0;font-size:13.5px}th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}th.what,td.what{text-align:left}th.after{font-weight:500;color:var(--myhome-text)}td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}td.what{color:var(--myhome-text-soft)}td.after{font-weight:500}a{color:var(--myhome-primary)}.refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}`,se=(r,t,e,i,n)=>a`<div class="row">
  <span class="what">${r}</span>
  <span class="value">${t}${e?a` ${e}`:l}</span>
  ${n?a`<span class="instead">${n}</span>`:l}
  ${i?a`<span class="from">${i}</span>`:l}
</div>`,ae=r=>a`<div>
  <label class="field-row">
    <span class="what">${r.label}</span>
    <input
      class="field"
      type="text"
      inputmode="decimal"
      .value=${r.value}
      ?disabled=${r.disabled}
      placeholder=${r.placeholder??""}
      aria-label=${r.ariaLabel??r.label}
      aria-invalid=${r.error?"true":"false"}
      @input=${t=>r.onInput(t.target.value)}
    />
    <span class="unit">${r.unit}</span>
  </label>
  ${r.error?a`<p class="field-error">${r.error}</p>`:l}
</div>`,y=r=>a`<button
  class="wide ${r.destructive?"destructive":""}"
  type="button"
  title=${r.title??""}
  ?disabled=${r.disabled??!1}
  @click=${r.onClick}
>
  ${r.label}
  ${r.note?a`<span class="note">${r.note}</span>`:l}
</button>`,E=(r,t,e,i=!1)=>a`<div class="foot">
  <button class="cta text" type="button" ?disabled=${i} @click=${t}>
    ${r}
  </button>
  ${e}
</div>`;var K=[...ie,...ve],Te=class extends g{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)){if(this.state.detail.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new b,this.state=q({view:"cover",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[$,k,R,z,Ee,Ce]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.detail,i=`${e.for??""}|${e.mode}`;if(i===this._focused)return;let n=this.renderRoot.querySelector("[data-heading]");n&&(this._focused=i,oe(()=>n))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}_label(e){return this.i18n.t(`options.step.calibration_edit.data.${e}`)}_unit(e){let i=ge[e];return i?this.i18n.t(i):""}_number(e,i){return this.i18n.number(i,x[e]??I[e]?.decimals??1)}_problem(e,i){return this.i18n.refusal(i,{key:this._label(e),min:I[e]?.min??0,max:I[e]?.max??0,cover:this.state.detail.answer?.cover.name??""})}_destination(){let e=this.state.detail.answer?.forget;return e?e.falls_back_to==="profile"?this.i18n.t("panel.detail.destination.profile",{profile:e.profile??""}):e.falls_back_to==="file"?this.i18n.t("panel.detail.destination.file"):this.i18n.t("panel.detail.destination.defaults"):""}render(){let e=this.state.detail;return e.loading?a`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`:e.answer?a`${this._head(e.answer.cover)}
    ${this.state.writeError?a`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:l}
    ${e.mode==="view"?this._view(e.answer.cover,e.answer.keys):l}
    ${e.mode==="edit"?this._edit(e.answer.keys):l}
    ${e.mode==="travel"?this._travel(e.answer.cover):l}
    ${e.mode==="correct"?this._correct():l}
    ${e.mode==="remove"?this._remove(e.answer.cover):l}`:a`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.unknown")}</h2>
        <p class="sub">
          ${e.error?this.i18n.refusal(e.error.translation_key,e.error.translation_placeholders??{}):""}
        </p>
        ${E(this.i18n.t("panel.common.action.retry"),this.actions.retry,a`<button class="cta secondary compact" type="button" @click=${this.actions.back}>
            ${this.i18n.t("panel.common.action.back")}
          </button>`)}
      </div>`}_head(e){let i=[e.area,e.height===null?this.i18n.t("panel.overview.cover.travel_unknown"):this.i18n.t("panel.overview.cover.travel",{travel:this.i18n.number(e.height,0)}),e.profile?this.i18n.t("panel.overview.cover.follows",{profile:e.profile}):null].filter(o=>!!o),n=e.level==="precise"?this.i18n.t("panel.detail.level_thorough"):e.level==="basic"?this.i18n.t("panel.detail.level_basic"):null;return a`<section class="card">
      <p class="sub">${i.join(" · ")}</p>
      <div class="chips">
        ${Pe(this.i18n,e.origin,e.profile,!1)}
        ${e.measured_at?a`<span class="chip"
              >${this.i18n.t("panel.detail.measured_at",{date:this.i18n.date(e.measured_at)})}${n?` · ${n}`:""}</span
            >`:l}
        ${e.verify_note!==null?a`<span class="chip"
              >${this.i18n.t("panel.detail.verify_note",{deviation:this.i18n.number(e.verify_note,1)})}</span
            >`:l}
      </div>
      ${e.profile_missing?a`<p class="warn" style="margin-top:12px;margin-bottom:0">
            ${this.i18n.t("panel.overview.cover.profile_missing",{profile:e.profile??""})}
          </p>`:l}
      ${e.profile_from_file?a`<p class="sub" style="margin-top:8px">
            ${this.i18n.t("panel.overview.cover.from_file")}
          </p>`:l}
    </section>`}_view(e,i){let n=K.map(p=>i.find(d=>d.key===p)).filter(p=>p!==void 0),o=e.has_own.length>0,s=o&&e.level!=="precise";return a`<section class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.values.title")}</h2>
        <p class="intro">${this.i18n.t("panel.detail.values.intro")}</p>
        <div class="rows">
          ${n.map(p=>this._valueRow(e,p))}
        </div>
      </section>
      <section class="card actions">
        ${y({label:this.i18n.t("panel.detail.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
        ${y({label:this.i18n.t("panel.detail.action.travel"),note:this.i18n.t("options.step.calibration_edit.data_description.height"),disabled:this._locked,onClick:()=>this.actions.mode("travel")})}
        ${y({label:this.i18n.t("panel.detail.action.assign"),disabled:this._locked,onClick:this.actions.assign})}
        ${e.profile?y({label:this.i18n.t("panel.overview.group.open"),note:this.i18n.t("panel.overview.group.profile",{profile:e.profile}),onClick:()=>this.actions.openProfile(e.profile)}):l}
        ${this._flowButton("panel.detail.action.measure_again","panel.detail.action.measure_again_note")}
        ${o?y({label:this.i18n.t("panel.detail.action.correct"),note:this.i18n.t("panel.detail.action.correct_note"),onClick:()=>this.actions.mode("correct")}):l}
        ${s?this._flowButton("panel.detail.action.thorough","panel.detail.action.thorough_note"):l}
        ${o?y({label:this.i18n.t("panel.detail.action.remove"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("remove")}):l}
      </section>`}_valueRow(e,i){let n=i.origin==="own"?this.i18n.t("panel.detail.source.own"):i.origin==="profile"?this.i18n.t("panel.detail.source.profile",{profile:e.profile??""}):i.origin==="file"?this.i18n.t("panel.detail.source.file"):this.i18n.t("panel.detail.source.default");return se(this._label(i.key),this._number(i.key,i.value),this._unit(i.key),n,i.own&&i.inherited_value!==null?this.i18n.t("panel.detail.edit.inherits",{value:this._number(i.key,i.inherited_value)}):null)}_flowButton(e,i){return y({label:`${this.i18n.t(e)} ↗`,note:this.i18n.t(i),title:this.i18n.t("panel.common.opens_configure"),onClick:n=>this.actions.openFlow(n.currentTarget)})}_edit(e){let i=this.state.detail.form,n=K.map(s=>e.find(p=>p.key===s)).filter(s=>s!==void 0),o=n.some(s=>w(s.key,i[s.key])!==null);return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.edit.title")}</h2>
      <div class="warn">${this.i18n.t("panel.detail.edit.intro")}</div>
      <div class="fields">
        ${n.map(s=>this._field(s))}
      </div>
      ${E(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||o}
          @click=${this.actions.saveValues}>
          ${this.i18n.t("panel.detail.edit.action.save")}
        </button>`,this.state.applying)}
    </section>`}_field(e){let i=this.state.detail.form[e.key],n=w(e.key,i),o=e.inherited_value===null?this.i18n.t("panel.detail.edit.empty"):this.i18n.t("panel.detail.edit.inherits",{value:this._number(e.key,e.inherited_value)});return ae({label:this._label(e.key),value:i??"",unit:this._unit(e.key),placeholder:o,error:n?this._problem(e.key,n):null,disabled:this.state.applying,onInput:s=>this.actions.field(e.key,s)})}_travel(e){let i=this.state.detail.form.height,n=w("height",i),o=this.state.detail.preview,s=o&&o.problem===null?K.filter(p=>o.values[p]!==void 0&&e.values[p]!==void 0):[];return a`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("options.step.calibration_edit.data.height")}
      </h2>
      <p class="intro">
        ${this.i18n.t("options.step.calibration_edit.data_description.height")}
      </p>
      ${ae({label:this.i18n.t("panel.review.travel.label"),ariaLabel:this.i18n.t("panel.review.travel.aria"),value:i??"",unit:this.i18n.t("panel.common.unit.centimetres"),placeholder:this.i18n.t("panel.review.travel.placeholder"),error:n?this._problem("height",n):null,disabled:this.state.applying,onInput:p=>this.actions.field("height",p)})}
      ${o&&o.problem!==null?a`<p class="field-error">${this._problem("height",o.problem)}</p>`:l}
      ${s.length>0?a`<table>
            <thead>
              <tr>
                <th class="what"></th>
                <th>${this.i18n.t("panel.review.before")}</th>
                <th class="after">${this.i18n.t("panel.review.after")}</th>
              </tr>
            </thead>
            <tbody>
              ${s.map(p=>a`<tr>
                  <td class="what">${this._label(p)}</td>
                  <td>${this._number(p,e.values[p])}</td>
                  <td class="after">
                    ${this._number(p,o.values[p])}
                  </td>
                </tr>`)}
            </tbody>
          </table>`:l}
      ${E(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||n!==null||M(i)}
          @click=${this.actions.saveTravel}>
          ${this.i18n.t("panel.common.action.save")}
        </button>`,this.state.applying)}
    </section>`}_correct(){return a`<section class="card actions">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.action.correct")}</h2>
      <p class="intro">${this.i18n.t("panel.detail.correct.intro")}</p>
      ${this._flowButton("panel.detail.correct.times","panel.detail.correct.times_note")}
      ${this._flowButton("panel.detail.correct.times_rolls","panel.detail.correct.times_rolls_note")}
      ${this._flowButton("panel.detail.correct.thorough","panel.detail.correct.thorough_note")}
      <div class="foot">
        <button class="cta text" type="button" @click=${()=>this.actions.mode("view")}>
          ${this.i18n.t("panel.common.action.back")}
        </button>
      </div>
    </section>`}_remove(e){let i=this.state.detail.answer?.forget;return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.remove.title")}</h2>
      <div class="danger">
        <p style="margin:0">
          ${this.i18n.t("panel.detail.remove.body",{cover:e.name,destination:this._destination()})}
        </p>
        ${i?.travel_stays?a`<p class="soft">${this.i18n.t("panel.detail.remove.travel_stays")}</p>`:l}
      </div>
      ${E(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.detail.remove.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-cover-detail")||customElements.define("myhome-cover-detail",Te);var j=["reference_height",...A],Yi=/^[A-Za-z0-9_]+$/,Ae=class extends g{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)){if(this.state.profile.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new b,this.state=q({view:"profile",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[$,k,R,z,Ce]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.profile,i=`${e.for??""}|${e.mode}`;if(i===this._focused)return;let n=this.renderRoot.querySelector("[data-heading]");n&&(this._focused=i,oe(()=>n))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}get _profile(){let e=this.state.profile.for;return this.state.overview?.profiles.find(i=>i.name===e)??null}get _followers(){let e=this._profile,i=this.state.overview?.covers??[];if(!e)return[];let n=new Set([...e.followers,...e.followers_from_file]);return i.filter(o=>n.has(o.unique_id))}_label(e){return e==="reference_height"?this.i18n.t("panel.profile.reference_travel"):this.i18n.t(`options.step.profile_edit.data.${e}`)}_unit(e){let i=ge[e];return i?this.i18n.t(i):""}_number(e,i){return this.i18n.number(i,x[e]??I[e]?.decimals??1)}_problem(e,i){return this.i18n.refusal(i,{key:this._label(e),min:I[e]?.min??0,max:I[e]?.max??0})}_ownKeys(e){return e.has_own.map(i=>this.i18n.t(`options.step.calibration_edit.data.${i}`)).join(", ")}render(){let e=this._profile;if(!this.state.overview)return a`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;if(!e)return a`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.unknown")}</h2>
        ${E(this.i18n.t("panel.common.action.back"),this.actions.back,l)}
      </div>`;let i=this.state.profile.mode;return a`${this._head(e)}
    ${this.state.writeError?a`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:l}
    ${i==="view"?this._view(e):l}
    ${i==="edit"?this._edit():l}
    ${i==="rename"?this._rename(e):l}
    ${i==="delete"?this._delete(e):l}`}_head(e){let n=(this.state.overview?.covers??[]).find(p=>p.unique_id===e.measured_on),o;e.measured_on&&e.measured_on_name&&e.measured_at?(o=this.i18n.t("panel.profile.provenance",{cover:e.measured_on_name,date:this.i18n.date(e.measured_at)}),n&&n.profile!==e.name&&(o+=` · ${n.profile?this.i18n.t("panel.profile.provenance_now_profile",{profile:n.profile}):this.i18n.t("panel.profile.provenance_now_none")}`)):e.measured_on&&e.measured_at?o=this.i18n.t("panel.overview.group.measured_on_gone",{date:this.i18n.date(e.measured_at)}):o=this.i18n.t("panel.profile.provenance_missing");let s=e.editable?this.i18n.t("panel.profile.stored"):this.i18n.t("panel.profile.from_file");return a`<section class="card">
      <p class="sub">${e.missing?o:`${s} · ${o}`}</p>
      ${e.missing?a`<p class="warn" style="margin:12px 0 0">
            ${this.i18n.t("panel.overview.group.values_unknown")}
          </p>`:l}
    </section>`}_view(e){let i=this._followers;return a`${e.missing?l:a`<section class="card">
            <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.values")}</h2>
            <div class="rows">
              ${j.map(n=>n==="reference_height"?e.reference_height===null?l:se(this._label(n),this._number(n,e.reference_height),this._unit(n),"",null):e.values[n]===void 0?l:se(this._label(n),this._number(n,e.values[n]),this._unit(n),"",null))}
            </div>
          </section>`}
      <section class="card">
        <h2 ?data-heading=${e.missing} tabindex="-1">
          ${i.length===0?this.i18n.t("panel.profile.followers.none"):i.length===1?this.i18n.t("panel.profile.followers.count_one"):this.i18n.t("panel.profile.followers.count",{count:i.length})}
        </h2>
        <p class="intro">${this.i18n.t("panel.profile.edit.intro")}</p>
        <div class="rows">
          ${i.map(n=>this._follower(n))}
        </div>
      </section>
      ${e.editable?a`<section class="card actions">
            ${y({label:this.i18n.t("panel.profile.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
            ${y({label:this.i18n.t("panel.profile.action.rename"),disabled:this._locked,onClick:()=>this.actions.mode("rename")})}
            ${y({label:this.i18n.t("panel.profile.action.delete"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("delete")})}
          </section>`:l}`}_follower(e){let n=A.every(o=>e.has_own.includes(o))?this.i18n.t("panel.profile.followers.measured"):e.has_own.length>0?this.i18n.t("panel.profile.followers.adjusted",{keys:this._ownKeys(e)}):this.i18n.t("panel.profile.followers.inherited");return a`<div class="row">
      <span class="what">
        <button
          class="cta text"
          type="button"
          style="padding:0;min-height:44px"
          @click=${()=>this.actions.openCover(e.unique_id)}
        >
          ${e.name}
        </button>
      </span>
      <span class="instead">${n}</span>
      ${e.profile_from_file?a`<span class="from">${this.i18n.t("panel.overview.cover.from_file")}</span>`:l}
    </div>`}_edit(){let e=this._followers,i=this.state.profile.form,n=j.some(s=>w(s,i[s])!==null||M(i[s])),o=e.length===1?this.i18n.t("panel.profile.edit.reach_one"):this.i18n.t("panel.profile.edit.reach_all",{count:e.length});return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.action.edit")}</h2>
      <div class="warn">
        <strong>${this.i18n.t("panel.profile.edit.reach",{target:o})}</strong>
        ${this.i18n.t("panel.profile.edit.intro")}
      </div>
      <div class="fields">
        ${j.map(s=>ae({label:this._label(s),value:i[s]??"",unit:this._unit(s),error:(()=>{let p=w(s,i[s]);return p?this._problem(s,p):null})(),disabled:this.state.applying,onInput:p=>this.actions.field(s,p)}))}
      </div>
      <h3>${this.i18n.t("panel.profile.impact.title")}</h3>
      <div class="rows">
        ${e.map(s=>this._impact(s,n))}
      </div>
      ${E(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||n}
          @click=${this.actions.saveValues}>
          ${e.length===1?this.i18n.t("panel.profile.edit.action.save_one"):this.i18n.t("panel.profile.edit.action.save",{count:e.length})}
        </button>`,this.state.applying)}
    </section>`}_impact(e,i){let n=A.every(p=>e.has_own.includes(p)),o=n?this.i18n.t("panel.profile.impact.state_measured"):e.has_own.length>0?this.i18n.t("panel.profile.impact.state_adjusted"):this.i18n.t("panel.profile.impact.state_inherited"),s;if(n)s=this.i18n.t("panel.profile.impact.no_change");else if(e.height===null)s=this.i18n.t("panel.profile.impact.no_travel");else if(i)s=this.i18n.t("panel.profile.impact.invalid");else{let p=(this.state.profile.impact??[]).find(d=>d.cover_unique_id===e.unique_id);if(!p||p.problem!==null)s=this.i18n.t("panel.common.loading");else if(s=A.filter(c=>!e.has_own.includes(c)&&e.values[c]!==void 0&&p.values[c]!==void 0).map(c=>`${this.i18n.t(`options.step.calibration_edit.data.${c}`)} ${this._number(c,e.values[c])} → ${this._number(c,p.values[c])}`).join(" · "),e.has_own.length>0){let c=this.i18n.t("panel.profile.impact.kept",{keys:this._ownKeys(e)});s=s?`${s} — ${c}`:c}}return a`<div class="row">
      <span class="what">${e.name}</span>
      <span class="instead">${o}</span>
      <span class="from" style="text-align:left">${s}</span>
    </div>`}_rename(e){let i=this.state.profile.newName,n=i.trim()!==""&&!Yi.test(i.trim()),o=n?this.i18n.refusal("invalid_name",{profile:i}):this.state.profile.nameError;return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.rename.title")}</h2>
      <p class="intro">${this.i18n.t("panel.profile.rename.rule")}</p>
      <label class="field-row">
        <span class="what">${this.i18n.t("panel.profile.rename.field")}</span>
        <input
          class="field"
          type="text"
          style="width:220px;text-align:left"
          .value=${i}
          ?disabled=${this.state.applying}
          aria-label=${this.i18n.t("panel.profile.rename.field")}
          aria-invalid=${o?"true":"false"}
          @input=${s=>this.actions.newName(s.target.value)}
        />
      </label>
      ${o?a`<p class="field-error" style="text-align:left">${o}</p>`:l}
      ${E(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||n||i.trim()===""||i.trim()===e.name}
          @click=${this.actions.rename}>
          ${this.i18n.t("panel.profile.rename.action")}
        </button>`,this.state.applying)}
    </section>`}_delete(e){let i=this._followers;return a`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("panel.profile.delete.title",{profile:e.name})}
      </h2>
      <div class="danger">
        ${i.length===0?a`<p style="margin:0">${this.i18n.t("panel.profile.followers.none")}</p>`:a`<p style="margin:0">${this.i18n.t("panel.profile.delete.affects")}</p>
              <ul>
                ${i.map(n=>a`<li>${n.name}</li>`)}
              </ul>`}
        <p>${this.i18n.t("panel.profile.delete.body")}</p>
      </div>
      ${E(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.profile.delete.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-profile-card")||customElements.define("myhome-profile-card",Ae);var li={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},pi=r=>(...t)=>({_$litDirective$:r,values:t}),Ie=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,i){this._$Ct=t,this._$AM=e,this._$Ci=i}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var di="important",Xi=" !"+di,ci=pi(class extends Ie{constructor(r){if(super(r),r.type!==li.ATTRIBUTE||r.name!=="style"||r.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(r){return Object.keys(r).reduce((t,e)=>{let i=r[e];return i==null?t:t+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${i};`},"")}update(r,[t]){let{style:e}=r.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(t)),this.render(t);for(let i of this.ft)t[i]==null&&(this.ft.delete(i),i.includes("-")?e.removeProperty(i):e[i]=null);for(let i in t){let n=t[i];if(n!=null){this.ft.add(i);let o=typeof n=="string"&&n.endsWith(Xi);i.includes("-")||o?e.setProperty(i,o?n.slice(0,-11):n,o?di:""):e[i]=n}}return S}});var hi=(r,t)=>r.summary?.note?a`<div class="stub">${r.summary.note}</div>`:l;var ui=(r,t)=>{let e=r.options??[];return e.length===0?l:a`<div class="options" role="group" aria-label=${r.title}>
    ${e.map(i=>a`<button
        class="option"
        type="button"
        aria-pressed=${i.current?"true":"false"}
        @click=${()=>t.fire(i.action)}
      >
        <span class="option-head">
          <strong class="option-title">${i.title}</strong>
          ${i.chip?a`<span class="chip neutral">${i.chip}</span>`:l}
        </span>
        ${i.meta?a`<span class="option-meta">${i.meta}</span>`:l}
      </button>`)}
  </div>`};var mi=(r,t)=>{let e=r.progress;if(!e)return a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let i=Math.max(0,Math.min(1,e.fraction))*100;return a`<div class="progress-card">
    ${e.text?a`<p class="instruction">${e.text}</p>`:l}
    <div
      class="progress-track"
      role="progressbar"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow=${Math.round(i)}
    >
      <div class="progress-bar" style=${`width:${i}%`}></div>
    </div>
    <p class="progress-eta" role="status">
      ${e.done?t.i18n.t("panel.screen.completed"):e.eta??""}
    </p>
  </div>`};var vi=(r,t)=>{let e=r.press;if(!e)return a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let i=e.state==="moving";return a`
    ${e.instruction?a`<p class="instruction">${e.instruction}</p>`:l}
    <div class="live">
      <div class="live-row">
        <span class="name">${t.i18n.t("panel.screen.motor")}</span>
        <span class="value ${i?"moving":""}">${e.motor??""}</span>
      </div>
      ${e.position?a`<div class="live-row">
            <span class="name">${t.i18n.t("panel.screen.position")}</span>
            <span class="value">${e.position}</span>
          </div>`:l}
    </div>
    ${e.note?a`<div
          class="note ${e.state==="problem"?"error":"success"}"
          role=${e.state==="problem"?"alert":"status"}
        >
          ${e.note}
        </div>`:l}
  `};var gi=(r,t)=>{let e=r.options??[];if(e.length===0&&!r.field)return a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let i=r.field;return a`
    <div class="options" role="group" aria-label=${r.title}>
      ${e.map(n=>a`<button
          class="option"
          type="button"
          aria-pressed=${n.current?"true":"false"}
          @click=${()=>t.fire(n.action)}
        >
          <strong class="option-title">${n.title}</strong>
          ${n.meta?a`<span class="option-meta">${n.meta}</span>`:l}
        </button>`)}
    </div>
    ${i?a`<div class="reading" style="margin-top:12px">
          <label for="gap">${i.label}</label>
          <div class="row">
            <input
              id="gap"
              inputmode="decimal"
              .value=${i.value}
              placeholder=${i.placeholder??""}
              aria-describedby=${i.error?"gap-error":l}
              aria-invalid=${i.error?"true":"false"}
              @input=${n=>t.fire("field",n.target.value)}
            />
            ${i.unit?a`<span class="unit">${i.unit}</span>`:l}
          </div>
          ${i.error?a`<p class="error" id="gap-error" role="alert">${i.error}</p>`:l}
        </div>`:l}
  `};var fi=(r,t)=>{let e=r.field;return e?a`<div class="reading ${e.big===!1?"":"big"}">
    <label for="reading">${e.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${e.value}
        placeholder=${e.placeholder??""}
        aria-describedby=${e.error?"reading-error":e.hint?"reading-hint":l}
        aria-invalid=${e.error?"true":"false"}
        @input=${i=>t.fire("field",i.target.value)}
      />
      ${e.unit?a`<span class="unit">${e.unit}</span>`:l}
    </div>
    ${e.hint?a`<p class="hint" id="reading-hint">${e.hint}</p>`:l}
    ${e.error?a`<p class="error" id="reading-error" role="alert">${e.error}</p>`:l}
  </div>`:a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`};var _i=(r,t)=>{let e=r.summary;return e?a`
    <div class="summary">
      ${e.rows.map(i=>a`<div class="summary-row">
          <span class="label">${i.label}</span>
          ${i.before?a`<span class="before" aria-label=${t.i18n.t("panel.review.before")}
                >${i.before}</span
              >`:l}
          <span class="after" aria-label=${t.i18n.t("panel.review.after")}>${i.after}</span>
        </div>`)}
      ${e.note?a`<p class="note-line">${e.note}</p>`:l}
    </div>
    ${e.code?a`<pre class="code">${e.code}</pre>`:l}
  `:a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`};var wi=(r,t)=>r.summary?.rows?.length?a`<div class="summary">
    ${r.summary.rows.map(e=>a`<div class="summary-row">
        <span class="label">${e.label}</span>
        <span class="after">${e.after}</span>
      </div>`)}
    ${r.summary.note?a`<p class="note-line">${r.summary.note}</p>`:l}
  </div>`:l;var bi=u`.text-column{min-width:0}.phase{margin:0 0 8px;font-size:12px;color:var(--myhome-text-soft)}.new-text{display:inline-block;margin:0 0 12px;background:var(--myhome-info-pastel);border-radius:10px;padding:3px 10px;font-size:12px;color:var(--myhome-text-soft)}.screen-title{margin:0 0 12px;font-size:20px;font-weight:500;line-height:1.3;display:flex;align-items:center;gap:10px}.outcome-icon{width:32px;height:32px;flex:0 0 32px;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;font-weight:600}.outcome-icon.saved{background:var(--myhome-success-pastel);color:var(--myhome-success)}.outcome-icon.saved:before{content:"\2713"}.outcome-icon.cancelled{background:var(--myhome-error-pastel);color:var(--myhome-error)}.outcome-icon.cancelled:before{content:"\2715"}.outcome-icon.expired{background:var(--myhome-warning-pastel);color:var(--myhome-warning)}.outcome-icon.expired:before{content:"\29d7"}.outcome-icon.problem{background:var(--myhome-error-pastel);color:var(--myhome-error)}.outcome-icon.problem:before{content:"!"}.drawing{height:230px;border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);margin:0 0 16px;background-color:var(--myhome-drawing-paper);background-repeat:no-repeat}.prose p{margin:0 0 12px;font-size:14.5px;line-height:1.6;text-wrap:pretty}.prose ul{margin:0 0 12px;padding-left:20px;font-size:14.5px;line-height:1.6}.prose .md-image{display:block;max-width:100%;border-radius:var(--myhome-radius);margin:0 0 12px}.big{width:100%;min-height:64px;border:none;border-radius:16px;font:inherit;font-size:16px;font-weight:600;cursor:pointer;background:var(--myhome-primary);color:var(--myhome-text-on-primary);box-shadow:var(--myhome-shadow)}.big.moving{background:var(--myhome-accent);color:var(--myhome-text)}.big[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default;box-shadow:none}.options{display:flex;flex-direction:column;gap:8px;margin:4px 0 0}.option{text-align:left;border-radius:10px;font:inherit;padding:14px;min-height:56px;cursor:pointer;color:inherit;border:1px solid var(--myhome-divider);background:var(--myhome-card)}.option[aria-pressed=true]{border-color:var(--myhome-primary);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.option .option-head{display:flex;align-items:center;gap:8px}.option .option-title{font-weight:500;flex:1;font-size:14.5px;line-height:1.4}.option .option-meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:3px}.live{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:14px 16px;display:flex;flex-direction:column;gap:8px;font-size:14px}.live-row{display:flex;justify-content:space-between;gap:12px}.live-row .name{color:var(--myhome-text-soft)}.live-row .value{font-variant-numeric:tabular-nums;font-weight:500}.live-row .value.moving{color:var(--myhome-warning);animation:myhome-pulse 1.2s ease-in-out infinite}@keyframes myhome-pulse{0%,to{opacity:1}50%{opacity:.55}}.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.instruction{margin:0 0 16px;font-size:16.5px;line-height:1.5;font-weight:500}.note{margin:14px 0 0;border-radius:8px;padding:12px 14px;font-size:14px;line-height:1.55}.note.success{background:var(--myhome-success-pastel)}.note.error{background:var(--myhome-error-pastel)}.note.info{background:var(--myhome-info-pastel)}.progress-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px}.progress-track{height:8px;border-radius:4px;background:var(--myhome-background-soft);overflow:hidden}.progress-bar{height:100%;background:var(--myhome-primary);border-radius:4px;transition:width .1s linear}.progress-eta{margin:10px 0 0;font-size:13px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}.reading{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:4px 0 0}.reading label{display:block;font-size:13.5px;margin:0 0 8px}.reading .row{display:flex;align-items:center;gap:10px}.reading input{flex:1;min-width:0;height:56px;border-radius:10px;border:1px solid var(--myhome-divider);background:var(--myhome-card);color:inherit;padding:0 14px;font:inherit;font-size:26px;font-variant-numeric:tabular-nums}.reading.big input{height:64px;font-size:32px}.reading .unit{font-size:16px;color:var(--myhome-text-soft)}.reading.big .unit{font-size:18px}.reading .hint{margin:8px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.reading .error{margin:8px 0 0;font-size:12.5px;color:var(--myhome-error);line-height:1.5}.summary{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:8px 16px;margin:4px 0 14px}.summary-row{display:flex;align-items:baseline;gap:8px;padding:9px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.summary-row:last-of-type{border-bottom:none}.summary-row .label{flex:1 1 130px;color:var(--myhome-text-soft)}.summary-row .before{color:var(--myhome-text-soft);font-variant-numeric:tabular-nums;text-decoration:line-through;opacity:.7}.summary-row .after{font-variant-numeric:tabular-nums;font-weight:500}.summary .note-line{margin:10px 0;font-size:12.5px;color:var(--myhome-text-soft)}.code{background:var(--myhome-background-soft);border-radius:8px;padding:12px 14px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-x:auto}.stub{margin:4px 0 0;background:var(--myhome-info-pastel);border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.55}`;var Zi=/^\/myhome_static\/[A-Za-z0-9._~\-/]+$/,Ji=/(^|\/)\.\.?(\/|$)/,yi=/^[A-Za-z0-9 %.,\-]+$/,Qi=r=>{if(!Zi.test(r.src)||Ji.test(r.src))return null;let t=r.size&&yi.test(r.size)?r.size:"100% auto",e=r.pos&&yi.test(r.pos)?r.pos:"50% 60%";return{backgroundImage:`url("${r.src}")`,backgroundSize:t,backgroundPosition:e}},Me=class extends g{constructor(){super();this._fire=(e,i)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:e,value:i,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new b}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[$,k,R,z,be,bi,u`:host{display:block;background:transparent}.screen{width:100%;max-width:480px;margin:0 auto;display:flex;flex-direction:column;position:relative}main{flex:1;padding:16px 16px 230px}.right{min-width:0}.footer{position:fixed;bottom:0;left:50%;transform:translate(-50%);width:100%;max-width:480px;padding:36px 16px calc(12px + env(safe-area-inset-bottom,0px));background:linear-gradient(to top,var(--myhome-background) calc(100% - 36px),transparent);z-index:25;display:flex;flex-direction:column;gap:10px}@media(min-width:900px){.screen{max-width:100%}main{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:0 44px;align-items:start;width:100%;max-width:1080px;margin:0 auto;padding:24px 32px 48px}main.single{display:block;max-width:560px}.right{position:sticky;top:76px}.footer{position:static;transform:none;width:auto;max-width:none;padding:0;background:none;margin-top:20px}}`]}_renderOperative(e,i){switch(e.model){case"scelta":return ui(e,i);case"pos":return mi(e,i);case"click":return vi(e,i);case"controllo":return gi(e,i);case"metro":return fi(e,i);case"riepilogo":return _i(e,i);case"esito":return wi(e,i);case"lettura":return hi(e,i);default:return l}}_renderFooter(e,i){let n=e.secondary??[];return!e.primary&&n.length===0?l:a`<div class="footer">
      ${e.primary?a`<button
            class="big ${e.press?.state==="moving"?"moving":""}"
            type="button"
            ?disabled=${e.primary.disabled}
            @click=${()=>this._fire(e.primary.action)}
          >
            ${e.primary.label}
          </button>`:l}
      ${n.map(o=>a`<button
          class="cta ${o.kind==="text"?"text":"secondary"}"
          type="button"
          ?disabled=${o.disabled}
          @click=${()=>i.fire(o.action)}
        >
          ${o.label}
        </button>`)}
    </div>`}render(){let e=this.model;if(!e)return l;let i={i18n:this.i18n,fire:this._fire},n=e.model==="pos",o=e.image?Qi(e.image):null;return a`<div class="screen">
      <main class=${n?"single":""}>
        <div class="text-column">
          ${e.phase?a`<p class="phase">
                ${this.i18n.t("panel.screen.phase",{phase:e.phase.label,index:e.phase.index,count:e.phase.count})}
              </p>`:l}
          ${e.newText?a`<p class="new-text">${this.i18n.t("panel.screen.new_text")}</p>`:l}
          <h1 class="screen-title">
            ${e.outcome?a`<span class="outcome-icon ${e.outcome}" aria-hidden="true"></span>`:l}
            <span>${e.title}</span>
          </h1>
          ${o?a`<div
                class="drawing"
                role="img"
                aria-label=${e.image?.alt??""}
                style=${ci(o)}
              ></div>`:l}
          ${e.body?a`<div class="prose">${W(e.body)}</div>`:l}
        </div>
        <div class="right">
          ${this._renderOperative(e,i)} ${this._renderFooter(e,i)}
        </div>
      </main>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",Me);var er=3e4,tr=7e3,et=400,tt=class extends g{constructor(){super();this._i18n=new b;this._router=new fe;this._store=new _e(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._snackTimer=null;this._previewTimer=null;this._travelTimer=null;this._impactTimer=null;this._previewSeq=0;this._onReturn=()=>{!this._started||document.hidden||this._refresh()};this._assignActions={search:e=>this._store.set({search:e}),room:e=>this._store.set({room:e}),clearFilters:()=>this._store.set({search:"",room:""}),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:(e,i)=>{if(this._locked)return;let{pending:n,withdrawn:o}=zt(this._store.state.pending,e,i);this._store.set({pending:n,dialog:null,armed:null,writeError:null}),this._store.announce(o?this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name}):this._i18n.t("panel.assign.announce.pending",{cover:e.name,target:i===null?this._i18n.t("panel.assign.target_none"):this._i18n.t("panel.assign.target_profile",{profile:i})})),this._schedulePreview()},withdraw:e=>{this._store.set({pending:this._store.state.pending.filter(i=>i.cover!==e.unique_id)}),this._store.announce(this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name})),this._schedulePreview()},discardAll:()=>{this._store.set({...we}),this._store.announce(this._i18n.t("panel.assign.announce.discarded"))},reorder:e=>{this._locked||!this._store.state.entryId||(this._store.set({order:e}),this._write(()=>Et(this.hass.connection,this._store.state.entryId,e),i=>{this._store.set({order:null}),this._store.setOverview(i.overview),this._snack(this._i18n.t("panel.toast.order_saved"),i.undo_token),this._store.announce(this._i18n.t("panel.assign.announce.reordered"))},i=>{this._store.set({order:null,writeError:null}),this._snack(i,null,!1)}))},setOrder:e=>this._store.set({order:e}),drag:e=>this._store.set({drag:e?{cover:e.unique_id,name:e.name,over:null,insert:null}:null}),over:e=>{let i=this._store.state.drag;i&&this._store.set({drag:{...i,over:e?.group??null,insert:e?{...e}:null}})},arm:e=>{this._store.set({armed:e?e.unique_id:null}),e&&this._store.announce(this._i18n.t("panel.assign.announce.armed"))},dialog:e=>this._store.set({dialog:e?e.unique_id:null}),review:e=>{this._store.set({review:e,writeError:null,heightsForced:!1}),e&&this._refreshPreview()},height:(e,i)=>{this._store.set({heights:{...this._store.state.heights,[e]:i}}),this._schedulePreview()},toggleShowAll:()=>this._store.set({showAll:!this._store.state.showAll}),confirm:()=>{this._confirm()},undo:()=>{this._undo()},announce:e=>this._store.announce(e)};this._detailActions={back:()=>this._navigate("/"),retry:()=>{this._store.set({detail:{...this._store.state.detail,loading:!0,error:null}}),this._loadDetail()},openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:()=>{let e=this._store.state.detail.for;this._store.set({dialog:e}),this._navigate("/")},mode:e=>{let i=this._store.state.detail,n=this._detailCover,o=e==="edit"?this._detailForm():e==="travel"?{height:n?.height!=null?this._i18n.number(n.height,0):""}:{};this._store.set({detail:{...i,mode:e,form:o,errors:{},preview:null,previewing:!1},writeError:null}),e==="travel"&&this._refreshTravelPreview()},field:(e,i)=>{let n=this._store.state.detail,o=e==="height"&&w("height",i)!==null;o&&(this._previewSeq+=1),this._store.set({detail:{...n,form:{...n.form,[e]:i},...o?{preview:null}:{}}}),e==="height"&&this._scheduleTravelPreview()},saveValues:()=>{this._saveValues()},saveTravel:()=>{this._saveTravel()},remove:()=>{this._removeMeasure()},openFlow:e=>this._openFlow(e)};this._profileActions={back:()=>this._navigate("/"),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),mode:e=>{let i=this._store.state.profile;this._store.set({profile:{...i,mode:e,form:e==="edit"?this._profileForm(this._profileRow):{},errors:{},newName:e==="rename"?i.for??"":"",nameError:"",impact:null,impacting:!1},writeError:null}),e==="edit"&&this._refreshImpact()},field:(e,i)=>{let n=this._store.state.profile;this._store.set({profile:{...n,form:{...n.form,[e]:i}}}),this._scheduleImpact()},newName:e=>this._store.set({profile:{...this._store.state.profile,newName:e,nameError:""}}),saveValues:()=>{this._saveProfile()},rename:()=>{this._renameProfile()},remove:()=>{this._deleteProfile()}};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[$,k,R,be,Kt,xe,u`.toolbar{display:flex;align-items:center;gap:8px;padding:0 8px;background:var(--myhome-header);color:var(--myhome-header-text);font-size:20px;font-weight:400;padding-top:env(safe-area-inset-top,0px);height:calc(56px + env(safe-area-inset-top,0px))}.toolbar .title{flex:1;min-width:0;margin:0;font-size:inherit;font-weight:inherit;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar select.gateway{font:inherit;font-size:13px;max-width:40%;min-height:44px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;padding:0 6px}.toolbar select.gateway option{color:var(--myhome-text);background:var(--myhome-card)}.toolbar button{width:48px;height:48px;flex:0 0 48px;border:0;border-radius:24px;background:transparent;color:inherit;font-size:20px;line-height:1;cursor:pointer}.content{padding:16px;max-width:1200px;margin:0 auto;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}.card.problem{background:var(--myhome-error-pastel);color:var(--myhome-text);padding:16px}.card.waiting{color:var(--myhome-text-soft);padding:16px}.soft{color:var(--myhome-text-soft);font-size:13px;margin-top:8px}.connection{margin:24px 0 0;font-size:12.5px;color:var(--myhome-text-soft)}a{color:var(--myhome-primary)}`]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(e=>this._onRoute(e)),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._stopPolling(),this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._previewTimer&&(clearTimeout(this._previewTimer),this._previewTimer=null),this._travelTimer&&(clearTimeout(this._travelTimer),this._travelTimer=null),this._impactTimer&&(clearTimeout(this._impactTimer),this._impactTimer=null);let e=this._unsubscribeWs;this._unsubscribeWs=null,e?.().catch(()=>{})}shouldUpdate(e){return e.size>1||!e.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(e){if(e.has("route")&&(this._router.setHostPath(this.route?.path),this._onRoute(this._router.current)),!(!e.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_languageOf(e){return e?.locale?.language||e?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,await this._loadTexts(),await this._refresh(),await this._loadDetail(),await this._listen())}async _loadTexts(){let e=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,e)}catch{}this._language=e,this.requestUpdate()}async _refresh(){try{let e=await yt(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(e)}catch(e){this._store.setError(C(e))}}async _listen(){try{this._unsubscribeWs=await kt(this.hass.connection,this._store.state.entryId,e=>this._onEvent(e)),this._store.set({connection:"live"}),this._stopPolling()}catch(e){ee(e)||console.warn("MyHOME panel: live updates are not available",C(e)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(e){if(e.type==="overview"){this._store.setOverview(e.overview),this._store.state.review&&this._schedulePreview(),this._store.state.detail.for&&this._loadDetail();return}if(e.type==="measuring"){let i=this._store.state.overview;if(!i)return;this._store.set({overview:{...i,measuring:e.cover_unique_id?{cover_unique_id:e.cover_unique_id,name:e.name??""}:null}}),e.cover_unique_id&&(this._store.set({armed:null,drag:null}),this._store.announce(this._i18n.t("panel.banner.measuring.body",{cover:e.name??""})))}}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},er))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}_onRoute(e){if(this._store.set({route:e}),e.view==="cover"){let i=e.params.id;this._store.state.detail.for!==i&&(this._store.set({detail:{...re,for:i,loading:!0}}),this._loadDetail())}else this._store.state.detail.for!==null&&this._store.set({detail:re});if(e.view==="profile"){let i=e.params.name;this._store.state.profile.for!==i&&this._store.set({profile:{...ne,for:i}})}else this._store.state.profile.for!==null&&this._store.set({profile:ne});this._started&&this._store.set({writeError:null})}get _version(){return this.panel?.config?.version??""}_navigate(e){this._router.navigate(e)}_renderMenuButton(){return this.narrow?Lt("ha-menu-button")?a`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:a`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>Ot(this)}
    >
      ☰
    </button>`:l}_renderBackButton(){return this._store.state.route.view==="overview"?l:a`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.back")}
      @click=${()=>this._navigate("/")}
    >
      ←
    </button>`}_renderPlaceholder(e,i){let n={id:"panel.common.not_yet",model:"lettura",title:e,body:i,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return a`<myhome-screen
      .model=${n}
      .i18n=${this._i18n}
      @myhome-screen-action=${o=>{o.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}get _locked(){let e=this._store.state;return e.overview?.measuring!=null||e.applying}async _confirm(){let e=this._store.state,i=e.entryId;if(this._locked||!i||e.pending.length===0)return;if(e.pending.filter(p=>{let d=e.overview?.covers.find(c=>c.unique_id===p.cover);return d!==void 0&&Nt(d,p)&&te(e.heights[p.cover])!==null}).length>0){this._store.set({heightsForced:!0}),this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));return}let o=Xe(e.pending,e.heights),s=e.order??void 0;this._store.announce(this._i18n.t("panel.assign.announce.applying")),await this._write(()=>Rt(this.hass.connection,i,o,s),p=>{this._store.set({...we}),this._store.setOverview(p.overview),this._snack(p.applied===1?this._i18n.t("panel.toast.assigned_one"):this._i18n.t("panel.toast.assigned",{count:p.applied}),p.undo_token)})}async _undo(){let e=this._store.state,i=e.snack?.undoToken;if(!i||!e.entryId)return;let n=e.entryId;this._clearSnack(),await this._write(()=>Mt(this.hass.connection,n,i),o=>{this._store.setOverview(o.overview),this._snack(this._i18n.t("panel.toast.undone"),null)})}async _write(e,i,n){this._store.set({applying:!0,writeError:null});try{let o=await e();this._store.set({applying:!1}),i(o)}catch(o){let s=C(o);this._store.set({applying:!1,writeError:s});let p=this._i18n.refusal(s.translation_key,s.translation_placeholders??{});this._store.announce(p),n?.(p)}}_snack(e,i,n=!0){this._clearSnack(),this._store.set({snack:{message:e,undoToken:i}}),n&&this._store.announce(e),this._snackTimer=setTimeout(()=>{this._snackTimer=null,this._store.set({snack:null})},tr)}_clearSnack(){this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._store.set({snack:null})}_schedulePreview(){this._store.state.review&&(this._previewTimer&&clearTimeout(this._previewTimer),this._previewTimer=setTimeout(()=>{this._previewTimer=null,this._refreshPreview()},et))}async _refreshPreview(){let e=this._store.state;if(!e.entryId||e.pending.length===0){this._store.set({preview:null});return}let i=++this._previewSeq;this._store.set({previewing:!0});try{let n=await ue(this.hass.connection,e.entryId,Xe(e.pending,e.heights));i===this._previewSeq&&this._store.set({preview:n.items,previewing:!1})}catch(n){i===this._previewSeq&&this._store.set({previewing:!1}),ee(n)||console.warn("MyHOME panel: the preview could not be read",C(n))}}get _detailCover(){let e=this._store.state,i=e.detail.for;return e.overview?.covers.find(n=>n.unique_id===i)??null}async _loadDetail(){let e=this._store.state,i=e.detail.for;if(!(!this._started||!this.hass||!i||!e.entryId))try{let n=await $t(this.hass.connection,e.entryId,i);if(this._store.state.detail.for!==i)return;this._store.set({detail:{...this._store.state.detail,answer:n,loading:!1,error:null}})}catch(n){if(this._store.state.detail.for!==i)return;this._store.set({detail:{...this._store.state.detail,answer:null,loading:!1,error:C(n)}})}}_detailForm(){let e=this._store.state.detail.answer,i={};for(let n of K){let o=e?.keys.find(s=>s.key===n);i[n]=o&&o.own?this._i18n.number(o.value,x[n]??1):""}return i}async _saveValues(){let e=this._store.state,i=e.detail.for;if(this._locked||!i||!e.entryId)return;let n={};for(let d of K){let c=e.detail.form[d];if(w(d,c)!==null)return;n[d]=M(c)?null:T(c??"")}let o=Object.values(n).every(d=>d===null),s=this._detailCover?.name??"",p=e.entryId;await this._write(()=>St(this.hass.connection,p,i,n),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{}}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(o?this._i18n.t("panel.toast.measure_removed",{cover:s,destination:this._destinationOf(d.overview,i)}):this._i18n.t("panel.toast.values_saved",{cover:s}),d.undo_token)})}async _saveTravel(){let e=this._store.state,i=e.detail.for,n=e.detail.form.height;if(this._locked||!i||!e.entryId||M(n)||w("height",n))return;let o=T(n??""),s=this._detailCover?.name??"",p=e.entryId;await this._write(()=>Pt(this.hass.connection,p,i,o),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{},preview:null}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.travel_saved",{cover:s}),d.undo_token)})}async _removeMeasure(){let e=this._store.state,i=e.detail.for;if(this._locked||!i||!e.entryId)return;let n=this._detailCover?.name??"",o=e.entryId;await this._write(()=>Ct(this.hass.connection,o,i),s=>{this._store.set({detail:{...this._store.state.detail,mode:"view"}}),this._store.setOverview(s.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.measure_removed",{cover:n,destination:s.falls_back_to==="profile"?this._i18n.t("panel.detail.destination.profile",{profile:s.profile??""}):s.falls_back_to==="file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}),s.undo_token)})}_destinationOf(e,i){let n=e.covers.find(o=>o.unique_id===i);return n?.origin==="inherited"||n?.origin==="adjusted"?this._i18n.t("panel.detail.destination.profile",{profile:n.profile??""}):n?.origin==="from_the_file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}_scheduleTravelPreview(){this._travelTimer&&clearTimeout(this._travelTimer),this._travelTimer=setTimeout(()=>{this._travelTimer=null,this._refreshTravelPreview()},et)}async _refreshTravelPreview(){let e=this._store.state,i=this._detailCover,n=e.detail.form.height;if(!e.entryId||!i||M(n)||w("height",n)!==null){this._store.set({detail:{...this._store.state.detail,preview:null}});return}let o=++this._previewSeq;this._store.set({detail:{...this._store.state.detail,previewing:!0}});try{let s=await ue(this.hass.connection,e.entryId,[{...Ze(i),height:T(n??"")}]);if(o!==this._previewSeq)return;this._store.set({detail:{...this._store.state.detail,preview:s.items[0]??null,previewing:!1}})}catch(s){o===this._previewSeq&&this._store.set({detail:{...this._store.state.detail,previewing:!1}}),ee(s)||console.warn("MyHOME panel: the preview could not be read",C(s))}}_openFlow(e){qt({source:e,entryId:this._store.state.entryId,onLeaving:()=>this._store.announce(this._i18n.t("panel.common.opens_configure"))})}_title(){let e=this._store.state,i=e.route;if(i.view==="cover"){let n=this._detailCover;return n?this._i18n.t("panel.detail.named",{cover:n.name}):this._i18n.t("panel.detail.title")}return i.view==="profile"?e.overview?.profiles.some(o=>o.name===i.params.name)?this._i18n.t("panel.profile.name",{profile:i.params.name}):this._i18n.t("panel.profile.title"):this._i18n.t("panel.overview.title")}get _profileRow(){let e=this._store.state;return e.overview?.profiles.find(i=>i.name===e.profile.for)??null}_followersOf(e){let i=this._store.state.overview?.covers??[];if(!e)return[];let n=new Set([...e.followers,...e.followers_from_file]);return i.filter(o=>n.has(o.unique_id))}_profileForm(e){let i={};for(let n of j){let o=n==="reference_height"?e?.reference_height:e?.values[n];i[n]=o==null?"":this._i18n.number(o,x[n]??0)}return i}_typedProfile(){let e=this._store.state.profile.form,i={};for(let n of j){if(M(e[n])||w(n,e[n])!==null)return null;i[n]=T(e[n]??"")}return i}async _saveProfile(){let e=this._store.state,i=e.profile.for,n=this._typedProfile();if(this._locked||!i||!e.entryId||!n)return;let{reference_height:o,...s}=n,p=e.entryId;await this._write(()=>Tt(this.hass.connection,p,i,s,o),d=>{this._store.set({profile:{...this._store.state.profile,mode:"view",impact:null}}),this._store.setOverview(d.overview),this._snack(d.affected.length===1?this._i18n.t("panel.toast.profile_saved_one",{profile:i}):this._i18n.t("panel.toast.profile_saved",{profile:i,count:d.affected.length}),d.undo_token)})}async _renameProfile(){let e=this._store.state,i=e.profile.for,n=e.profile.newName.trim();if(this._locked||!i||!e.entryId||!n||n===i)return;let o=e.entryId;await this._write(()=>At(this.hass.connection,o,i,n),s=>{this._store.setOverview(s.overview),this._navigate(`/profile/${encodeURIComponent(n)}`),this._snack(this._i18n.t("panel.toast.profile_renamed",{profile:n}),s.undo_token)},s=>this._store.set({profile:{...this._store.state.profile,nameError:s},writeError:null}))}async _deleteProfile(){let e=this._store.state,i=e.profile.for;if(this._locked||!i||!e.entryId)return;let n=e.entryId;await this._write(()=>It(this.hass.connection,n,i),o=>{this._store.setOverview(o.overview),this._navigate("/"),this._snack(this._i18n.t("panel.toast.profile_deleted",{profile:i}),o.undo_token)})}_scheduleImpact(){this._impactTimer&&clearTimeout(this._impactTimer),this._impactTimer=setTimeout(()=>{this._impactTimer=null,this._refreshImpact()},et)}async _refreshImpact(){let e=this._store.state,i=this._typedProfile(),n=e.profile.for,o=this._followersOf(this._profileRow);if(!e.entryId||!n||!i||o.length===0){this._store.set({profile:{...this._store.state.profile,impact:null}});return}let s=++this._previewSeq;this._store.set({profile:{...this._store.state.profile,impacting:!0}});try{let p=await ue(this.hass.connection,e.entryId,o.map(d=>Ze(d)),{[n]:i});if(s!==this._previewSeq)return;this._store.set({profile:{...this._store.state.profile,impact:p.items,impacting:!1}})}catch(p){s===this._previewSeq&&this._store.set({profile:{...this._store.state.profile,impacting:!1}}),ee(p)||console.warn("MyHOME panel: the impact preview could not be read",C(p))}}_renderView(){let e=this._store.state;if(e.status==="loading")return a`<div class="card waiting" role="status">
        ${this._i18n.t("panel.common.loading")}
      </div>`;if(e.status==="error"||!e.overview){let n=e.error;return a`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(n?.translation_key,n?.translation_placeholders??{})}
        </div>
        <div class="soft">${n?`${n.code}: ${n.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._refresh()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${L}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?a` · ${this._version}`:l}
        </div>
      </div>`}let i=e.route;return i.view==="cover"?a`<myhome-cover-detail
        .i18n=${this._i18n}
        .state=${e}
        .actions=${this._detailActions}
      ></myhome-cover-detail>`:i.view==="profile"?a`<myhome-profile-card
        .i18n=${this._i18n}
        .state=${e}
        .actions=${this._profileActions}
      ></myhome-profile-card>`:i.view!=="overview"?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):a`<myhome-overview
      .i18n=${this._i18n}
      .state=${e}
      .actions=${this._assignActions}
    ></myhome-overview>`}render(){let e=this._store.state,i=this._title(),n=e.overview?.measuring??null,o=e.route.view!=="overview";return a`
      <div class="toolbar">
        ${this._renderMenuButton()} ${this._renderBackButton()}
        <h1 class="title">${i}</h1>
        ${this._renderGatewayPicker()}
      </div>
      ${n?jt(this._i18n,n.name,L):l}
      <div class="content">
        ${Wt(e.announce)} ${this._renderView()}
        ${e.connection==="polling"&&e.status==="ready"?a`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:l}
      </div>
      <!--
        The overview draws its own five strips, because three of them are about a gesture
        it owns. The routed cards have no gestures and two of the five still apply to them:
        a write in the air, and what it came to with "Annulla" beside it.
      -->
      ${o&&e.applying?$e(this._i18n):l}
      ${o&&e.snack&&!e.applying?ke(this._i18n,e.snack.message,e.snack.undoToken?()=>{this._undo()}:null):l}
    `}_renderGatewayPicker(){let e=this._store.state,i=e.overview?.entries??[],n=i.find(s=>s.entry_id===e.entryId);if(i.length<=1)return l;let o=this._i18n.t("panel.common.gateway",{gateway:n?.title??""});return a`<select
      class="gateway"
      aria-label=${o}
      .value=${e.entryId??""}
      ?disabled=${e.applying}
      @change=${s=>{this._switchGateway(s.target.value)}}
    >
      ${i.map(s=>a`<option value=${s.entry_id} ?selected=${s.entry_id===e.entryId}>
          ${s.title}
        </option>`)}
    </select>`}async _switchGateway(e){if(!e||e===this._store.state.entryId)return;let i=this._unsubscribeWs;this._unsubscribeWs=null,await i?.().catch(()=>{}),this._clearSnack(),this._store.set({...we,entryId:e,detail:re,profile:ne,search:"",room:"",snack:null}),this._navigate("/"),await this._refresh(),await this._listen()}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",tt);export{tt as MyHomeCalibrationPanel};
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
lit-html/directive.js:
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

lit-html/directives/style-map.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
