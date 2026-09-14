/* MyHOME calibration panel */
var pe=globalThis,de=pe.ShadowRoot&&(pe.ShadyCSS===void 0||pe.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Ne=Symbol(),pt=new WeakMap,V=class{constructor(i,e,t){if(this._$cssResult$=!0,t!==Ne)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=i,this.t=e}get styleSheet(){let i=this.o,e=this.t;if(de&&i===void 0){let t=e!==void 0&&e.length===1;t&&(i=pt.get(e)),i===void 0&&((this.o=i=new CSSStyleSheet).replaceSync(this.cssText),t&&pt.set(e,i))}return i}toString(){return this.cssText}},dt=n=>new V(typeof n=="string"?n:n+"",void 0,Ne),u=(n,...i)=>{let e=n.length===1?n[0]:i.reduce((t,r,o)=>t+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+n[o+1],n[0]);return new V(e,n,Ne)},ct=(n,i)=>{if(de)n.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of i){let t=document.createElement("style"),r=pe.litNonce;r!==void 0&&t.setAttribute("nonce",r),t.textContent=e.cssText,n.appendChild(t)}},qe=de?n=>n:n=>n instanceof CSSStyleSheet?(i=>{let e="";for(let t of i.cssRules)e+=t.cssText;return dt(e)})(n):n;var{is:Ai,defineProperty:Ii,getOwnPropertyDescriptor:Mi,getOwnPropertyNames:Li,getOwnPropertySymbols:Oi,getPrototypeOf:zi}=Object,ce=globalThis,ht=ce.trustedTypes,Di=ht?ht.emptyScript:"",Hi=ce.reactiveElementPolyfillSupport,Y=(n,i)=>n,Fe={toAttribute(n,i){switch(i){case Boolean:n=n?Di:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,i){let e=n;switch(i){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},mt=(n,i)=>!Ai(n,i),ut={attribute:!0,type:String,converter:Fe,reflect:!1,useDefault:!1,hasChanged:mt};Symbol.metadata??=Symbol("metadata"),ce.litPropertyMetadata??=new WeakMap;var C=class extends HTMLElement{static addInitializer(i){this._$Ei(),(this.l??=[]).push(i)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(i,e=ut){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(i)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(i,e),!e.noAccessor){let t=Symbol(),r=this.getPropertyDescriptor(i,t,e);r!==void 0&&Ii(this.prototype,i,r)}}static getPropertyDescriptor(i,e,t){let{get:r,set:o}=Mi(this.prototype,i)??{get(){return this[e]},set(a){this[e]=a}};return{get:r,set(a){let p=r?.call(this);o?.call(this,a),this.requestUpdate(i,p,t)},configurable:!0,enumerable:!0}}static getPropertyOptions(i){return this.elementProperties.get(i)??ut}static _$Ei(){if(this.hasOwnProperty(Y("elementProperties")))return;let i=zi(this);i.finalize(),i.l!==void 0&&(this.l=[...i.l]),this.elementProperties=new Map(i.elementProperties)}static finalize(){if(this.hasOwnProperty(Y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Y("properties"))){let e=this.properties,t=[...Li(e),...Oi(e)];for(let r of t)this.createProperty(r,e[r])}let i=this[Symbol.metadata];if(i!==null){let e=litPropertyMetadata.get(i);if(e!==void 0)for(let[t,r]of e)this.elementProperties.set(t,r)}this._$Eh=new Map;for(let[e,t]of this.elementProperties){let r=this._$Eu(e,t);r!==void 0&&this._$Eh.set(r,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(i){let e=[];if(Array.isArray(i)){let t=new Set(i.flat(1/0).reverse());for(let r of t)e.unshift(qe(r))}else i!==void 0&&e.push(qe(i));return e}static _$Eu(i,e){let t=e.attribute;return t===!1?void 0:typeof t=="string"?t:typeof i=="string"?i.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(i=>this.enableUpdating=i),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(i=>i(this))}addController(i){(this._$EO??=new Set).add(i),this.renderRoot!==void 0&&this.isConnected&&i.hostConnected?.()}removeController(i){this._$EO?.delete(i)}_$E_(){let i=new Map,e=this.constructor.elementProperties;for(let t of e.keys())this.hasOwnProperty(t)&&(i.set(t,this[t]),delete this[t]);i.size>0&&(this._$Ep=i)}createRenderRoot(){let i=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ct(i,this.constructor.elementStyles),i}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(i=>i.hostConnected?.())}enableUpdating(i){}disconnectedCallback(){this._$EO?.forEach(i=>i.hostDisconnected?.())}attributeChangedCallback(i,e,t){this._$AK(i,t)}_$ET(i,e){let t=this.constructor.elementProperties.get(i),r=this.constructor._$Eu(i,t);if(r!==void 0&&t.reflect===!0){let o=(t.converter?.toAttribute!==void 0?t.converter:Fe).toAttribute(e,t.type);this._$Em=i,o==null?this.removeAttribute(r):this.setAttribute(r,o),this._$Em=null}}_$AK(i,e){let t=this.constructor,r=t._$Eh.get(i);if(r!==void 0&&this._$Em!==r){let o=t.getPropertyOptions(r),a=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:Fe;this._$Em=r;let p=a.fromAttribute(e,o.type);this[r]=p??this._$Ej?.get(r)??p,this._$Em=null}}requestUpdate(i,e,t,r=!1,o){if(i!==void 0){let a=this.constructor;if(r===!1&&(o=this[i]),t??=a.getPropertyOptions(i),!((t.hasChanged??mt)(o,e)||t.useDefault&&t.reflect&&o===this._$Ej?.get(i)&&!this.hasAttribute(a._$Eu(i,t))))return;this.C(i,e,t)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(i,e,{useDefault:t,reflect:r,wrapped:o},a){t&&!(this._$Ej??=new Map).has(i)&&(this._$Ej.set(i,a??e??this[i]),o!==!0||a!==void 0)||(this._$AL.has(i)||(this.hasUpdated||t||(e=void 0),this._$AL.set(i,e)),r===!0&&this._$Em!==i&&(this._$Eq??=new Set).add(i))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let i=this.scheduleUpdate();return i!=null&&await i,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[r,o]of this._$Ep)this[r]=o;this._$Ep=void 0}let t=this.constructor.elementProperties;if(t.size>0)for(let[r,o]of t){let{wrapped:a}=o,p=this[r];a!==!0||this._$AL.has(r)||p===void 0||this.C(r,void 0,o,p)}}let i=!1,e=this._$AL;try{i=this.shouldUpdate(e),i?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(t){throw i=!1,this._$EM(),t}i&&this._$AE(e)}willUpdate(i){}_$AE(i){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(i)),this.updated(i)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(i){return!0}update(i){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(i){}firstUpdated(i){}};C.elementStyles=[],C.shadowRootOptions={mode:"open"},C[Y("elementProperties")]=new Map,C[Y("finalized")]=new Map,Hi?.({ReactiveElement:C}),(ce.reactiveElementVersions??=[]).push("2.1.2");var Ve=globalThis,vt=n=>n,he=Ve.trustedTypes,gt=he?he.createPolicy("lit-html",{createHTML:n=>n}):void 0,xt="$lit$",z=`lit$${Math.random().toFixed(9).slice(2)}$`,$t="?"+z,Ni=`<${$t}>`,F=document,Z=()=>F.createComment(""),Q=n=>n===null||typeof n!="object"&&typeof n!="function",Ye=Array.isArray,qi=n=>Ye(n)||typeof n?.[Symbol.iterator]=="function",Ue=`[ 	
\f\r]`,X=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ft=/-->/g,_t=/>/g,N=RegExp(`>|${Ue}(?:([^\\s"'>=/]+)(${Ue}*=${Ue}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),wt=/'/g,bt=/"/g,kt=/^(?:script|style|textarea|title)$/i,Xe=n=>(i,...e)=>({_$litType$:n,strings:i,values:e}),s=Xe(1),fn=Xe(2),_n=Xe(3),A=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),yt=new WeakMap,q=F.createTreeWalker(F,129);function Rt(n,i){if(!Ye(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return gt!==void 0?gt.createHTML(i):i}var Fi=(n,i)=>{let e=n.length-1,t=[],r,o=i===2?"<svg>":i===3?"<math>":"",a=X;for(let p=0;p<e;p++){let d=n[p],c,m,h=-1,v=0;for(;v<d.length&&(a.lastIndex=v,m=a.exec(d),m!==null);)v=a.lastIndex,a===X?m[1]==="!--"?a=ft:m[1]!==void 0?a=_t:m[2]!==void 0?(kt.test(m[2])&&(r=RegExp("</"+m[2],"g")),a=N):m[3]!==void 0&&(a=N):a===N?m[0]===">"?(a=r??X,h=-1):m[1]===void 0?h=-2:(h=a.lastIndex-m[2].length,c=m[1],a=m[3]===void 0?N:m[3]==='"'?bt:wt):a===bt||a===wt?a=N:a===ft||a===_t?a=X:(a=N,r=void 0);let _=a===N&&n[p+1].startsWith("/>")?" ":"";o+=a===X?d+Ni:h>=0?(t.push(c),d.slice(0,h)+xt+d.slice(h)+z+_):d+z+(h===-2?p:_)}return[Rt(n,o+(n[e]||"<?>")+(i===2?"</svg>":i===3?"</math>":"")),t]},J=class n{constructor({strings:i,_$litType$:e},t){let r;this.parts=[];let o=0,a=0,p=i.length-1,d=this.parts,[c,m]=Fi(i,e);if(this.el=n.createElement(c,t),q.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(r=q.nextNode())!==null&&d.length<p;){if(r.nodeType===1){if(r.hasAttributes())for(let h of r.getAttributeNames())if(h.endsWith(xt)){let v=m[a++],_=r.getAttribute(h).split(z),H=/([.?@])?(.*)/.exec(v);d.push({type:1,index:o,name:H[2],strings:_,ctor:H[1]==="."?Be:H[1]==="?"?Ke:H[1]==="@"?je:B}),r.removeAttribute(h)}else h.startsWith(z)&&(d.push({type:6,index:o}),r.removeAttribute(h));if(kt.test(r.tagName)){let h=r.textContent.split(z),v=h.length-1;if(v>0){r.textContent=he?he.emptyScript:"";for(let _=0;_<v;_++)r.append(h[_],Z()),q.nextNode(),d.push({type:2,index:++o});r.append(h[v],Z())}}}else if(r.nodeType===8)if(r.data===$t)d.push({type:2,index:o});else{let h=-1;for(;(h=r.data.indexOf(z,h+1))!==-1;)d.push({type:7,index:o}),h+=z.length-1}o++}}static createElement(i,e){let t=F.createElement("template");return t.innerHTML=i,t}};function W(n,i,e=n,t){if(i===A)return i;let r=t!==void 0?e._$Co?.[t]:e._$Cl,o=Q(i)?void 0:i._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),o===void 0?r=void 0:(r=new o(n),r._$AT(n,e,t)),t!==void 0?(e._$Co??=[])[t]=r:e._$Cl=r),r!==void 0&&(i=W(n,r._$AS(n,i.values),r,t)),i}var We=class{constructor(i,e){this._$AV=[],this._$AN=void 0,this._$AD=i,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(i){let{el:{content:e},parts:t}=this._$AD,r=(i?.creationScope??F).importNode(e,!0);q.currentNode=r;let o=q.nextNode(),a=0,p=0,d=t[0];for(;d!==void 0;){if(a===d.index){let c;d.type===2?c=new ee(o,o.nextSibling,this,i):d.type===1?c=new d.ctor(o,d.name,d.strings,this,i):d.type===6&&(c=new Ge(o,this,i)),this._$AV.push(c),d=t[++p]}a!==d?.index&&(o=q.nextNode(),a++)}return q.currentNode=F,r}p(i){let e=0;for(let t of this._$AV)t!==void 0&&(t.strings!==void 0?(t._$AI(i,t,e),e+=t.strings.length-2):t._$AI(i[e])),e++}},ee=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(i,e,t,r){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=i,this._$AB=e,this._$AM=t,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let i=this._$AA.parentNode,e=this._$AM;return e!==void 0&&i?.nodeType===11&&(i=e.parentNode),i}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(i,e=this){i=W(this,i,e),Q(i)?i===l||i==null||i===""?(this._$AH!==l&&this._$AR(),this._$AH=l):i!==this._$AH&&i!==A&&this._(i):i._$litType$!==void 0?this.$(i):i.nodeType!==void 0?this.T(i):qi(i)?this.k(i):this._(i)}O(i){return this._$AA.parentNode.insertBefore(i,this._$AB)}T(i){this._$AH!==i&&(this._$AR(),this._$AH=this.O(i))}_(i){this._$AH!==l&&Q(this._$AH)?this._$AA.nextSibling.data=i:this.T(F.createTextNode(i)),this._$AH=i}$(i){let{values:e,_$litType$:t}=i,r=typeof t=="number"?this._$AC(i):(t.el===void 0&&(t.el=J.createElement(Rt(t.h,t.h[0]),this.options)),t);if(this._$AH?._$AD===r)this._$AH.p(e);else{let o=new We(r,this),a=o.u(this.options);o.p(e),this.T(a),this._$AH=o}}_$AC(i){let e=yt.get(i.strings);return e===void 0&&yt.set(i.strings,e=new J(i)),e}k(i){Ye(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,t,r=0;for(let o of i)r===e.length?e.push(t=new n(this.O(Z()),this.O(Z()),this,this.options)):t=e[r],t._$AI(o),r++;r<e.length&&(this._$AR(t&&t._$AB.nextSibling,r),e.length=r)}_$AR(i=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);i!==this._$AB;){let t=vt(i).nextSibling;vt(i).remove(),i=t}}setConnected(i){this._$AM===void 0&&(this._$Cv=i,this._$AP?.(i))}},B=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(i,e,t,r,o){this.type=1,this._$AH=l,this._$AN=void 0,this.element=i,this.name=e,this._$AM=r,this.options=o,t.length>2||t[0]!==""||t[1]!==""?(this._$AH=Array(t.length-1).fill(new String),this.strings=t):this._$AH=l}_$AI(i,e=this,t,r){let o=this.strings,a=!1;if(o===void 0)i=W(this,i,e,0),a=!Q(i)||i!==this._$AH&&i!==A,a&&(this._$AH=i);else{let p=i,d,c;for(i=o[0],d=0;d<o.length-1;d++)c=W(this,p[t+d],e,d),c===A&&(c=this._$AH[d]),a||=!Q(c)||c!==this._$AH[d],c===l?i=l:i!==l&&(i+=(c??"")+o[d+1]),this._$AH[d]=c}a&&!r&&this.j(i)}j(i){i===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,i??"")}},Be=class extends B{constructor(){super(...arguments),this.type=3}j(i){this.element[this.name]=i===l?void 0:i}},Ke=class extends B{constructor(){super(...arguments),this.type=4}j(i){this.element.toggleAttribute(this.name,!!i&&i!==l)}},je=class extends B{constructor(i,e,t,r,o){super(i,e,t,r,o),this.type=5}_$AI(i,e=this){if((i=W(this,i,e,0)??l)===A)return;let t=this._$AH,r=i===l&&t!==l||i.capture!==t.capture||i.once!==t.once||i.passive!==t.passive,o=i!==l&&(t===l||r);r&&this.element.removeEventListener(this.name,this,t),o&&this.element.addEventListener(this.name,this,i),this._$AH=i}handleEvent(i){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,i):this._$AH.handleEvent(i)}},Ge=class{constructor(i,e,t){this.element=i,this.type=6,this._$AN=void 0,this._$AM=e,this.options=t}get _$AU(){return this._$AM._$AU}_$AI(i){W(this,i)}};var Ui=Ve.litHtmlPolyfillSupport;Ui?.(J,ee),(Ve.litHtmlVersions??=[]).push("3.3.3");var Et=(n,i,e)=>{let t=e?.renderBefore??i,r=t._$litPart$;if(r===void 0){let o=e?.renderBefore??null;t._$litPart$=r=new ee(i.insertBefore(Z(),o),o,void 0,e??{})}return r._$AI(n),r};var Ze=globalThis,f=class extends C{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let i=super.createRenderRoot();return this.renderOptions.renderBefore??=i.firstChild,i}update(i){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(i),this._$Do=Et(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return A}};f._$litElement$=!0,f.finalized=!0,Ze.litElementHydrateSupport?.({LitElement:f});var Wi=Ze.litElementPolyfillSupport;Wi?.({LitElement:f});(Ze.litElementVersions??=[]).push("4.2.2");var Pt={"panel.assign.action.discard_all":"Discard everything","panel.assign.action.review":"Review and confirm","panel.assign.action.review_hint":"Review and confirm the assignments","panel.assign.action.withdraw":"Withdraw this change","panel.assign.announce.applying":"The changes are being applied.","panel.assign.announce.armed":"Tap the destination group.","panel.assign.announce.discarded":"Every pending change has been discarded.","panel.assign.announce.drag_cancelled":"Drag cancelled.","panel.assign.announce.missing_travel":"Some covers have no travel.","panel.assign.announce.pending":"“{cover}” is pending, towards {target}. Nothing is written yet.","panel.assign.announce.reordered":"Order updated: it will be remembered.","panel.assign.announce.withdrawn":"“{cover}” goes back where it was: the change is withdrawn.","panel.assign.armed":"Tap the destination group for “{cover}”","panel.assign.drop_zone":"Take out of the profile — drop here","panel.assign.handle":"Move {cover} to another group, or reorder it","panel.assign.handle_hint":"Drag to assign or reorder, Enter to pick from a list","panel.assign.pending.all_own":"All values its own: nothing changes","panel.assign.pending.count":"{count} pending changes — nothing is written yet","panel.assign.pending.count_one":"1 pending change — nothing is written yet","panel.assign.pending.route":"{from} → {to}","panel.assign.pending.some_own":"Own values: those stay","panel.assign.target_none":"“No profile”","panel.assign.target_profile":"the profile “{profile}”","panel.banner.applying.body":"The covers are unavailable for a few seconds","panel.banner.applying.title":"The changes are being applied…","panel.banner.measuring.action.resume":"Resume the session","panel.banner.measuring.action.stop":"End it","panel.banner.measuring.body":"A guided calibration is using “{cover}”. Until the session ends, this panel only reads: nothing is written.","panel.banner.measuring.title":"Measurement in progress","panel.common.action.back":"Back","panel.common.action.cancel":"Cancel","panel.common.action.close":"Close","panel.common.action.configure":"Open Configure","panel.common.action.hide_all":"Hide the roll coefficients","panel.common.action.menu":"Open the Home Assistant menu","panel.common.action.retry":"Try again","panel.common.action.save":"Save","panel.common.action.show_all":"Show every value, roll coefficients included","panel.common.all_rooms":"All rooms","panel.common.gateway":"Gateway {gateway}","panel.common.loading":"Loading…","panel.common.not_yet":"This screen arrives in a later version. Until then “Configure” does everything it will do.","panel.common.opens_configure":"This opens the Configure dialog. The panel refreshes on its own when it closes.","panel.common.polling":"Live updates are not available on this version: the page refreshes on its own every 30 seconds.","panel.common.reconnected":"Home Assistant is answering again: this page has just been read afresh.","panel.common.required":"This field cannot be left empty.","panel.common.room_filter":"Filter by room","panel.common.search":"Search for a cover","panel.common.unit.centimetres":"cm","panel.common.unit.seconds":"s","panel.detail.action.assign":"Assign to a profile…","panel.detail.action.correct":"Correct…","panel.detail.action.correct_note":"If it stops in the wrong place: times only, times and rolls, or the thorough calibration only","panel.detail.action.edit":"Edit the values by hand","panel.detail.action.measure_again":"Measure again","panel.detail.action.measure_again_note":"Full basic calibration, in the dialog","panel.detail.action.remove":"Remove the measurement…","panel.detail.action.thorough":"Thorough calibration","panel.detail.action.thorough_note":"On top: readings at 25 and 75 % per direction, and a check","panel.detail.action.travel":"Set the curtain travel…","panel.detail.correct.intro":"The correction opens the Configure dialog on the path chosen. When it comes back, the panel refreshes on its own.","panel.detail.correct.thorough":"Thorough calibration only","panel.detail.correct.thorough_note":"Readings at 25 and 75 % per direction, and a check","panel.detail.correct.times":"Times only","panel.detail.correct.times_note":"One run per direction, the rolls stay","panel.detail.correct.times_rolls":"Times and rolls","panel.detail.correct.times_rolls_note":"Full basic calibration","panel.detail.destination.defaults":"the default values","panel.detail.destination.file":"the values of the configuration file","panel.detail.destination.profile":"the values inherited from the profile “{profile}”","panel.detail.edit.action.save":"Save the values","panel.detail.edit.empty":"empty = nothing to say","panel.detail.edit.inherits":"inherits {value}","panel.detail.edit.intro":"These values count for this cover alone and beat both the profile and the file. A field left empty is not a zero: it means “nothing to say about this one”, and the value goes back to coming from the profile or from the file. Emptying every field is the same as removing the measurement.","panel.detail.edit.title":"Edit the values by hand","panel.detail.level_basic":"basic calibration","panel.detail.level_thorough":"thorough calibration","panel.detail.measured_at":"Measured on {date}","panel.detail.named":"Cover “{cover}”","panel.detail.remove.action":"Remove the measurement","panel.detail.remove.body":"The measurements made on “{cover}” will be removed and cannot be recovered. The cover will go back to using {destination}.","panel.detail.remove.title":"Remove the measurement?","panel.detail.remove.travel_stays":"The curtain travel stays: somebody measured it with a tape.","panel.detail.source.default":"default value","panel.detail.source.file":"from the configuration file","panel.detail.source.own":"own value, measured on this cover","panel.detail.source.profile":"inherited from the profile “{profile}”","panel.detail.title":"Cover detail","panel.detail.unknown":"This gateway has no cover with that identifier.","panel.detail.values.intro":"What the cover is using right now, value by value, with where it comes from: a value of its own always wins; then the assigned profile, then the file, then the defaults.","panel.detail.values.title":"Values in use","panel.detail.verify_note":"{deviation} cm out at the check","panel.dialog.option.current":"current","panel.dialog.option.none":"No profile","panel.dialog.option.none_meta":"Values from the configuration file, or the defaults. The travel and the values of its own stay.","panel.dialog.option.profile":"Profile “{profile}”","panel.dialog.option.profile_meta":"{travel} cm · ascent {opening} s · descent {closing} s","panel.dialog.subtitle":"“{cover}” — the choice stays pending until it is confirmed.","panel.dialog.title":"Which profile?","panel.error.no_connection":"Home Assistant is not answering. The panel will try again.","panel.error.not_found":"The panel could not read this gateway.","panel.firstrun.action.measure":"Measure a cover","panel.firstrun.body":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.firstrun.how":"A profile is not written, it is measured. Pick one representative cover and measure it once, with the guided calibration: about three minutes. Similar covers can then follow it.","panel.firstrun.note":"This opens the Configure dialog: that is where the measuring happens. When it is done, the profile appears here.","panel.firstrun.title":"No profile yet","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.cover.follows":"follows “{profile}”","panel.overview.cover.from_file":"The configuration file assigns this profile: it is changed there, not here.","panel.overview.cover.origin_adjusted":"Adjusted","panel.overview.cover.origin_inherited":"Inherited","panel.overview.cover.profile_missing":"The profile “{profile}” is no longer defined: this cover is running on its own configuration.","panel.overview.cover.travel":"travel {travel} cm","panel.overview.cover.travel_needed":"travel to be entered","panel.overview.cover.travel_unknown":"travel not recorded","panel.overview.explanation":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.overview.group.count":"{count} covers","panel.overview.group.count_one":"1 cover","panel.overview.group.empty":"No cover in this group.","panel.overview.group.from_file":"Defined in the configuration file, and read-only from here.","panel.overview.group.measured_on":"Measured on {cover} · {date}","panel.overview.group.measured_on_gone":"Measured on a cover this gateway no longer has · {date}","panel.overview.group.missing":"This profile is not defined any more: the covers below have quietly fallen back to their own configuration.","panel.overview.group.no_profile":"No profile","panel.overview.group.no_profile_note":"Values from the configuration file, or the defaults. It is not a fault: a cover with measurements of its own sits perfectly well here.","panel.overview.group.open":"Open the profile card","panel.overview.group.profile":"Profile “{profile}”","panel.overview.group.provenance_missing":"Where it was measured is not recorded.","panel.overview.group.values":"Reference travel {travel} cm · ascent {opening} s · descent {closing} s · slats {slat} s","panel.overview.group.values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.no_basic_covers":"Every cover of this gateway reports its own position, so there is no travel model to calibrate and nothing for this panel to do.","panel.overview.no_basic_covers_title":"Nothing to calibrate on this gateway","panel.overview.no_results":"No cover matches this search.","panel.overview.summary":"Profiles: {profiles} · Basic covers: {covers}","panel.overview.title":"Profiles and covers","panel.profile.action.delete":"Delete the profile…","panel.profile.action.edit":"Edit the values…","panel.profile.action.rename":"Rename…","panel.profile.delete.action":"Delete the profile","panel.profile.delete.affects":"It affects these covers:","panel.profile.delete.body":"They will go back to the values of the configuration file, where those exist, or to the defaults. Their travels and their own values stay. The profile's measurements cannot be recovered.","panel.profile.delete.title":"Delete the profile “{profile}”?","panel.profile.edit.action.save":"Apply to {count} covers","panel.profile.edit.action.save_one":"Apply to 1 cover","panel.profile.edit.intro":"A change to the profile changes everything for the covers that inherit its values, and only the inherited values for the adjusted ones: the values of their own stay, key by key.","panel.profile.edit.reach":"The change reaches {target}","panel.profile.edit.reach_all":"every one of the {count} covers that follow the profile","panel.profile.edit.reach_one":"1 cover","panel.profile.followers.adjusted":"adjusted: own values for {keys}","panel.profile.followers.count":"{count} covers follow it","panel.profile.followers.count_one":"1 cover follows it","panel.profile.followers.inherited":"inherited","panel.profile.followers.measured":"measured: nothing inherited","panel.profile.followers.none":"No cover follows it.","panel.profile.from_file":"Profile of the configuration file: read-only here.","panel.profile.impact.invalid":"correct the fields to see the preview","panel.profile.impact.kept":"own values stay: {keys}","panel.profile.impact.no_change":"no change: all values are its own","panel.profile.impact.no_travel":"travel not recorded: it will use the profile's values as they are","panel.profile.impact.state_adjusted":"adjusted: only the inherited values change","panel.profile.impact.state_inherited":"inherited: everything changes","panel.profile.impact.state_measured":"measured","panel.profile.impact.title":"Impact preview","panel.profile.name":"Profile “{profile}”","panel.profile.provenance":"Measured on {cover} · {date}","panel.profile.provenance_missing":"Where it was measured is not recorded.","panel.profile.provenance_now_none":"now follows no profile","panel.profile.provenance_now_profile":"now follows “{profile}”","panel.profile.reference_travel":"Reference travel","panel.profile.rename.action":"Rename","panel.profile.rename.field":"New name of the profile","panel.profile.rename.rule":"Letters, digits and underscores only: no spaces, no accents — the name is also a key of the configuration file. The rename follows every cover that uses the profile.","panel.profile.rename.title":"Rename the profile","panel.profile.stored":"Stored profile","panel.profile.title":"Profile card","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.profile.values":"Values of the profile","panel.review.action.back":"Back to the overview","panel.review.action.confirm":"Confirm {count} assignments","panel.review.action.confirm_one":"Confirm 1 assignment","panel.review.action.missing_travel":"{count} travels missing","panel.review.action.missing_travel_one":"1 travel missing","panel.review.after":"After","panel.review.before":"Before","panel.review.intro":"The changes are written all at once. For each cover, this is what it will really use: the profile's values brought to its own travel.","panel.review.note.all_own":"It has values of its own for everything: nothing changes. The profile would only count for values removed later on.","panel.review.note.back_to_defaults":"The default values come back: the position in per cent will be a rough estimate. The travel and any value of its own stay.","panel.review.note.back_to_file":"The values of the configuration file come back. The travel and any value of its own stay.","panel.review.note.scaled":"Values of the profile “{profile}” (measured on {reference} cm) brought to a travel of {travel} cm.","panel.review.note.some_own":"It has some values of its own: those stay. Only the inherited values change.","panel.review.title":"Review and confirm","panel.review.travel.aria":"Curtain travel in centimetres","panel.review.travel.hint":"A profile is the measurement of one cover with a certain travel, and it is brought to the others in proportion. The travel of these is not known: measure the distance the bottom edge covers from fully closed to fully open, and write it in centimetres (decimals with a comma or with a point).","panel.review.travel.label":"Curtain travel","panel.review.travel.placeholder":"e.g. 145","panel.review.travel.required":"The travel is needed, in centimetres.","panel.review.travel.title":"How far does the curtain of these covers run?","panel.screen.completed":"Completed","panel.screen.motor":"Motor","panel.screen.new_text":"new text — not translated yet","panel.screen.not_in_this_version":"This step belongs to the guided calibration, which moves into the panel in a later version.","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.position":"Estimated position","panel.screen.progress":"Positioning progress","panel.toast.action.undo":"Undo","panel.toast.assigned":"{count} assignments applied","panel.toast.assigned_one":"1 assignment applied","panel.toast.measure_removed":"Measurement removed: “{cover}” now uses {destination}.","panel.toast.order_saved":"The new order will be remembered.","panel.toast.profile_deleted":"Profile “{profile}” deleted: the covers go back to the file or to the defaults.","panel.toast.profile_renamed":"Renamed to “{profile}”: the rename follows every cover that uses it.","panel.toast.profile_saved":"Profile “{profile}” updated: {count} covers reached.","panel.toast.profile_saved_one":"Profile “{profile}” updated: 1 cover reached.","panel.toast.travel_saved":"The travel of “{cover}” is saved: the profile is brought to this measurement.","panel.toast.undone":"Changes undone: everything as it was.","panel.toast.values_saved":"The values of “{cover}” are saved: they beat the profile and the file."};var Qe=Pt,Mn=Object.keys(Qe);var Ki=/^\/myhome_static\/[A-Za-z0-9._~\-/]+$/,ji=/(^|\/)\.\.?(\/|$)/,Je=n=>Ki.test(n)&&!ji.test(n),St=/^[A-Za-z0-9 %.,\-]+$/,Tt=n=>{if(!Je(n.src))return null;let i=n.size&&St.test(n.size)?n.size:"100% auto",e=n.pos&&St.test(n.pos)?n.pos:"50% 60%";return{backgroundImage:`url("${n.src}")`,backgroundSize:i,backgroundPosition:e}};var Gi=/^!\[([^\]]*)\]\(([^)\s]+)\)$/;var ue=n=>{let i=[],e=n.split("**"),t=e.length%2===0;return e.forEach((r,o)=>{if(!r)return;let a=o%2===1&&!(t&&o===e.length-1);i.push(a?s`<strong>${r}</strong>`:s`<span>${r}</span>`)}),i},Vi=n=>/^\s*[-*]\s+/.test(n),K=n=>{let i=(n||"").replace(/\r\n/g,`
`).split(/\n{2,}/),e=[];for(let t of i){let r=t.trim();if(!r)continue;let o=Gi.exec(r);if(o){e.push(Je(o[2])?s`<img class="md-image" src=${o[2]} alt=${o[1]} />`:s`<p>${ue(o[1])}</p>`);continue}let a=r.split(`
`);if(a.every(Vi)){e.push(s`<ul>
          ${a.map(p=>s`<li>${ue(p.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}e.push(s`<p>
        ${a.map((p,d)=>d===0?ue(p):[s`<br />`,...ue(p)])}
      </p>`)}return s`${e}`};var I=n=>n&&typeof n=="object"&&"code"in n?n:{code:"unknown_error",message:String(n)},Ct=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/overview",...i?{entry_id:i}:{}}),At=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/texts",language:i}),It=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_detail",entry_id:i,cover_unique_id:e}),me=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/preview",entry_id:i,items:e,...t?{profile_values:t}:{}}),Mt=(n,i,e)=>n.subscribeMessage(e,{type:"myhome/calibration/subscribe",...i?{entry_id:i}:{}}),te=n=>I(n).code==="unknown_command",Lt=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/assign",entry_id:i,assignments:e,...t?{order:t}:{}}),Ot=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/reorder",entry_id:i,order:e,...t!==void 0?{profile:t}:{}}),zt=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/set_travel",entry_id:i,cover_unique_id:e,height:t}),Dt=(n,i,e,t,r)=>n.sendMessagePromise({type:"myhome/calibration/cover_edit",entry_id:i,cover_unique_id:e,overrides:t,...r!==void 0?{height:r}:{}}),Ht=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_forget",entry_id:i,cover_unique_id:e}),Nt=(n,i,e,t,r)=>n.sendMessagePromise({type:"myhome/calibration/profile_edit",entry_id:i,name:e,values:t,reference_height:r}),qt=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/profile_rename",entry_id:i,name:e,new_name:t}),Ft=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/profile_delete",entry_id:i,name:e}),Ut=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/undo",entry_id:i,undo_token:e});var Yi=/\{([A-Za-z0-9_]+)\}/g,et=(n,i)=>i?n.replace(Yi,(e,t)=>Object.prototype.hasOwnProperty.call(i,t)?String(i[t]):e):n,y=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this.language="en";this.loaded=!1}async load(i,e){let t=await At(i,e);this._texts=t.texts??{},this.language=t.language,this.loaded=!0,this._numbers.clear(),this._dates=null}t(i,e){let t=this._lookup(i);if(t!==null)return et(t,e);let r=Qe[i];return et(r??i,e)}md(i,e){return K(this.t(i,e))}refusal(i,e){let t=i?this._lookup(`exceptions.${i}.message`):null;return t!==null?et(t,e):this.t("panel.error.not_found")}origin(i,e){return this.t(`selector.calibration_origin.options.${i}`,{profile:e??""})}number(i,e){let t=this._numbers.get(e);return t||(t=new Intl.NumberFormat(this.language,{minimumFractionDigits:e,maximumFractionDigits:e}),this._numbers.set(e,t)),t.format(i)}date(i){let e=new Date(i);return Number.isNaN(e.getTime())?i:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(e))}_lookup(i){let e=this._texts;for(let t of i.split(".")){if(e===null||typeof e!="object")return null;e=e[t]}return typeof e=="string"?e:null}};var Wt=n=>typeof customElements<"u"&&customElements.get(n)!==void 0;var Bt=n=>{n.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var ve=(n,i)=>{let e=ge(n.unique_id,i);return e?e.to:n.profile??null},ge=(n,i)=>i.find(e=>e.cover===n),Kt=(n,i,e)=>{let t=n.filter(r=>r.cover!==i.unique_id);return e===(i.profile??null)?{pending:t,withdrawn:!0}:{pending:[...t,{cover:i.unique_id,to:e}],withdrawn:!1}},jt=(n,i)=>{let e=new Map(n.covers.map(o=>[o.unique_id,o]));if(!i)return[...n.covers].sort((o,a)=>o.order_index-a.order_index);let t=new Set,r=[];for(let o of i){let a=e.get(o);a&&!t.has(o)&&(t.add(o),r.push(a))}for(let o of n.covers)t.has(o.unique_id)||r.push(o);return r},tt=(n,i,e)=>{let t=n.filter(o=>o!==i),r=t.length;if(e.beforeId){let o=t.indexOf(e.beforeId);r=o<0?t.length:o}else if(e.afterId){let o=t.indexOf(e.afterId);r=o<0?t.length:o+1}return[...t.slice(0,r),i,...t.slice(r)]},Gt=(n,i,e)=>{let t=e.filter(r=>r!==i).at(-1)??null;return tt(n,i,{beforeId:null,afterId:t})},it=(n,i)=>n.map(e=>{let t=i[e.cover],r=t===void 0?void 0:M(t);return{cover_unique_id:e.cover,profile:e.to,...r==null?{}:{height:r}}}),M=n=>{let i=n.trim().replace(",",".");if(!i)return null;let e=Number(i);return Number.isFinite(e)?e:null},Xi=20,Zi=500,ie=n=>{if(n===void 0||n.trim()==="")return"missing_travel";let i=M(n);return i===null?"not_a_number":i<Xi||i>Zi?"out_of_range":null},nt=n=>({cover_unique_id:n.unique_id,profile:n.profile_from_file?null:n.profile??null}),Vt=(n,i)=>i.to!==null&&n.height===null,L=["opening_time","closing_time","slat_time","opening_roll","closing_roll"],ne=["opening_time","closing_time","slat_time"],fe=["opening_roll","closing_roll"],$={opening_time:1,closing_time:1,slat_time:1,opening_roll:2,closing_roll:2};var O={opening_time:{min:1,max:600,decimals:1},closing_time:{min:1,max:600,decimals:1},slat_time:{min:0,max:60,decimals:1},opening_roll:{min:1,max:5,decimals:2},closing_roll:{min:1,max:5,decimals:2},height:{min:20,max:500,decimals:0},reference_height:{min:20,max:500,decimals:0}},_e={opening_time:"panel.common.unit.seconds",closing_time:"panel.common.unit.seconds",slat_time:"panel.common.unit.seconds",opening_roll:null,closing_roll:null,height:"panel.common.unit.centimetres",reference_height:"panel.common.unit.centimetres"},b=(n,i)=>{let e=(i??"").trim();if(e==="")return null;let t=M(e);if(t===null)return"not_a_number";let r=O[n];return r&&(t<r.min||t>r.max)?"out_of_range":null},k=n=>(n??"").trim()==="";var R="/config/integrations/integration/myhome";var rt="dialog-data-entry-flow",Qi=()=>typeof customElements<"u"&&customElements.get(rt)!==void 0,Yt=n=>{history.pushState(null,"",n),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))},Xt=n=>Qi()?(n.source.dispatchEvent(new CustomEvent("show-dialog",{bubbles:!0,composed:!0,detail:{dialogTag:rt,dialogImport:()=>Promise.resolve(),dialogParams:{startFlowHandler:n.entryId,domain:"myhome"}}})),setTimeout(()=>{document.querySelector(rt)||(n.onLeaving(),Yt(R))},400),"waiting"):(n.onLeaving(),Yt(R),"page");var Ji={view:"overview",params:{},path:"/"},Zt=n=>{let i="/"+(n||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(i==="/")return Ji;let e=i.slice(1).split("/"),t=e.slice(1).join("/"),r=t;try{r=decodeURIComponent(t)}catch{}return e[0]==="cover"&&t?{view:"cover",params:{id:r},path:i}:e[0]==="profile"&&t?{view:"profile",params:{name:r},path:i}:e[0]==="calibrate"&&t?{view:"calibrate",params:{session:r},path:i}:{view:"unknown",params:{},path:i}};var we=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(i){this._onChange=i,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(i){let e=i||"/";if(e===this._fromHost)return;let t=this.current.path;this._fromHost=e,this.current.path!==t&&this._emit()}get current(){let i=typeof location<"u"?location.hash:"";return i&&i.length>1?Zt(i.slice(1)):Zt(this._fromHost)}navigate(i){let e="#"+(i.startsWith("/")?i:"/"+i);location.hash!==e&&(location.hash=e)}_emit(){this._onChange(this.current)}};var re={for:null,answer:null,loading:!1,error:null,mode:"view",form:{},errors:{},preview:null,previewing:!1},oe={for:null,mode:"view",form:{},errors:{},newName:"",nameError:"",impact:null,impacting:!1},U=n=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:n,search:"",room:"",announce:"",pending:[],order:null,drag:null,armed:null,dialog:null,review:!1,heights:{},heightsForced:!1,showAll:!1,preview:null,previewing:!1,applying:!1,snack:null,writeError:null,detail:re,profile:oe}),ye={pending:[],order:null,heights:{},heightsForced:!1,preview:null,previewing:!1,review:!1,writeError:null},be=class{constructor(i){this._subscribers=new Set;this._state=U(i)}get state(){return this._state}subscribe(i){return this._subscribers.add(i),()=>this._subscribers.delete(i)}set(i){this._state={...this._state,...i};for(let e of this._subscribers)e(this._state)}setOverview(i){this.set({overview:i,entryId:i.entry_id,status:"ready",error:null})}setError(i){this.set({status:"error",error:i})}announce(i){this.set({announce:""}),this.set({announce:i})}};var E=u`:host{--myhome-text-on-primary: var(--text-primary-color, #ffffff);--myhome-snack-action: var(--snack-action-color, #ffc107);--myhome-primary: var(--primary-color, #03a9f4);--myhome-accent: var(--accent-color, #ff9800);--myhome-text: var(--primary-text-color, #212121);--myhome-text-soft: var(--secondary-text-color, #727272);--myhome-text-off: var(--disabled-text-color, #bdbdbd);--myhome-background: var(--primary-background-color, #fafafa);--myhome-background-soft: var(--secondary-background-color, #e5e5e5);--myhome-card: var(--card-background-color, #ffffff);--myhome-divider: var(--divider-color, rgba(0, 0, 0, .12));--myhome-error: var(--error-color, #db4437);--myhome-warning: var(--warning-color, #ffa600);--myhome-success: var(--success-color, #43a047);--myhome-info: var(--info-color, #039be5);--myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));--myhome-header-text: var(--app-header-text-color, #ffffff);--myhome-radius: var(--ha-card-border-radius, 12px);--myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, .14));--myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));--myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));--myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));--myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));--myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));--myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));--myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));--myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));--myhome-primary-ink: color-mix(in srgb, var(--myhome-primary) 50%, var(--myhome-text));--myhome-error-ink: color-mix(in srgb, var(--myhome-error) 50%, var(--myhome-text));--myhome-warning-ink: color-mix(in srgb, var(--myhome-warning) 50%, var(--myhome-text));--myhome-success-ink: color-mix(in srgb, var(--myhome-success) 50%, var(--myhome-text));--myhome-info-ink: color-mix(in srgb, var(--myhome-info) 50%, var(--myhome-text));--myhome-text-soft-ink: color-mix(in srgb, var(--myhome-text-soft) 50%, var(--myhome-text));--myhome-field-border: color-mix(in srgb, var(--myhome-text-soft) 80%, var(--myhome-card));--myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);display:block;min-height:100%;color:var(--myhome-text);background:var(--myhome-background)}*,*:before,*:after{box-sizing:border-box}:host * :focus-visible{outline:2px solid var(--myhome-primary-ink);outline-offset:2px}@media(prefers-reduced-motion:reduce){:host *{animation-duration:.001ms!important;transition-duration:.001ms!important}}`,P=u`.card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}`,S=u`.cta{min-height:48px;padding:0 24px;border-radius:24px;border:none;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font:inherit;font-size:15px;font-weight:500;cursor:pointer}.cta.secondary{background:transparent;border:1px solid var(--myhome-primary-ink);color:var(--myhome-primary-ink)}.cta.text{background:transparent;border:none;color:var(--myhome-primary-ink);padding:0 12px}.cta.destructive{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}.cta[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.cta.compact{min-height:44px;padding:0 18px;border-radius:22px;font-size:14px}`,D=u`.field{height:44px;border-radius:8px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:var(--myhome-text);padding:0 12px;font:inherit;font-size:14px}.field:disabled{color:var(--myhome-text-off)}`,xe=u`.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0}`;var Jt=n=>s`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${n}</div>`,se=n=>{requestAnimationFrame(()=>{let i=n();i&&i.focus()})};var $e=class{constructor(){this._root=null;this._onKey=i=>{if(i.key!=="Tab"||!this._root)return;let e=Qt(this._root);if(e.length===0){i.preventDefault(),this._root.focus();return}let t=e[0],r=e[e.length-1],o=this._root.getRootNode().activeElement;i.shiftKey&&(o===t||o===this._root)?(i.preventDefault(),r.focus()):!i.shiftKey&&o===r&&(i.preventDefault(),t.focus())}}hold(i){this.release(),this._root=i,i.addEventListener("keydown",this._onKey),se(()=>Qt(i)[0]??i)}release(){this._root?.removeEventListener("keydown",this._onKey),this._root=null}},Qt=n=>Array.from(n.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter(i=>i.offsetParent!==null||i===n);var ei=u`.measuring{max-width:1200px;margin:16px auto 0;padding:12px 16px;border-radius:var(--myhome-radius);background:var(--myhome-warning-pastel);display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.measuring strong{color:var(--myhome-warning-ink);font-weight:500}.measuring .body{flex:1 1 320px;line-height:1.5}.measuring .links{display:flex;gap:16px}.measuring a{color:var(--myhome-primary-ink);min-height:44px;display:inline-flex;align-items:center}`,ti=(n,i,e)=>s`<div class="measuring" role="status" aria-live="polite">
    <strong>${n.t("panel.banner.measuring.title")}</strong>
    <span class="body">${n.t("panel.banner.measuring.body",{cover:i})}</span>
    <span class="links">
      <a href=${e}>${n.t("panel.banner.measuring.action.resume")}</a>
      <a href=${e}>${n.t("panel.banner.measuring.action.stop")}</a>
    </span>
  </div>`;var ii={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},ni=n=>(...i)=>({_$litDirective$:n,values:i}),ke=class{constructor(i){}get _$AU(){return this._$AM._$AU}_$AT(i,e,t){this._$Ct=i,this._$AM=e,this._$Ci=t}_$AS(i,e){return this.update(i,e)}update(i,e){return this.render(...e)}};var ri="important",en=" !"+ri,Re=ni(class extends ke{constructor(n){if(super(n),n.type!==ii.ATTRIBUTE||n.name!=="style"||n.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(n){return Object.keys(n).reduce((i,e)=>{let t=n[e];return t==null?i:i+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${t};`},"")}update(n,[i]){let{style:e}=n.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(i)),this.render(i);for(let t of this.ft)i[t]==null&&(this.ft.delete(t),t.includes("-")?e.removeProperty(t):e[t]=null);for(let t in i){let r=i[t];if(r!=null){this.ft.add(t);let o=typeof r=="string"&&r.endsWith(en);t.includes("-")||o?e.setProperty(t,o?r.slice(0,-11):r,o?ri:""):e[t]=r}}return A}});var Ee=u`.sk{--sk-base: var(--myhome-background-soft)}.sk-bar{height:12px;border-radius:6px;background:linear-gradient(90deg,var(--sk-base) 25%,var(--myhome-card) 50%,var(--sk-base) 75%);background-size:400% 100%;animation:sk-slide 1.4s linear infinite}@keyframes sk-slide{0%{background-position:100% 0}to{background-position:0 0}}.sk-intro{max-width:72ch;margin:8px 0 16px;display:flex;flex-direction:column;gap:8px}.sk-controls{display:flex;gap:12px;margin:0 0 16px}.sk-controls .sk-bar{height:44px;border-radius:8px}.sk-groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.sk-groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(300px,1fr);align-items:start}}.sk-group{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.sk-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider);display:flex;flex-direction:column;gap:8px}.sk-body{padding:8px;display:flex;flex-direction:column;gap:2px}.sk-row{min-height:48px;padding:8px;display:flex;flex-direction:column;gap:8px;justify-content:center}.sk-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:0 0 16px;max-width:720px;display:flex;flex-direction:column;gap:12px}`,g=(n,i)=>s`<div
    class="sk-bar"
    aria-hidden="true"
    style=${Re(i?{width:n,height:i}:{width:n})}
  ></div>`,ot=()=>s`<div class="sk-row">${g("62%")}${g("40%","10px")}${g("28%","18px")}</div>`,oi=()=>s`<div class="sk-group">
    <div class="sk-head">${g("45%","16px")}${g("80%","10px")}${g("60%","10px")}</div>
    <div class="sk-body">${ot()}${ot()}${ot()}</div>
  </div>`,si=n=>s`<div class="sk" role="status" aria-busy="true" aria-label=${n.t("panel.common.loading")}>
    <div class="sk-intro">${g("92%","14px")}${g("74%","14px")}${g("36%","12px")}</div>
    <div class="sk-controls">${g("300px")}${g("160px")}</div>
    <div class="sk-groups">${oi()}${oi()}</div>
  </div>`,Pe=n=>s`<div class="sk" role="status" aria-busy="true" aria-label=${n.t("panel.common.loading")}>
    <div class="sk-card">
      ${g("40%","16px")}${g("70%","10px")}${g("100%")}${g("100%")}${g("55%")}
    </div>
    <div class="sk-card">${g("35%","16px")}${g("100%","44px")}${g("100%","44px")}</div>
  </div>`;var Se=u`.strip{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translate(-50%);max-width:92vw;box-sizing:border-box;box-shadow:var(--myhome-shadow)}.drop-zone{z-index:45;padding:14px 28px;min-height:48px;display:flex;align-items:center;border-radius:24px;font-size:14px;font-weight:500;border:2px dashed var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text-soft)}.drop-zone.over{border:2px solid var(--myhome-primary-ink);color:var(--myhome-primary-ink)}.dark{background:var(--myhome-text);color:var(--myhome-background);border-radius:8px;font-size:14px}.armed{z-index:40;padding:10px 16px;display:flex;gap:16px;align-items:center}.armed .what{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-width:0}.applying{z-index:70;padding:12px 20px}.applying .under{display:block;font-size:12px;opacity:.75;margin-top:2px}.snack{z-index:70;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:8px}.dark button{min-height:44px;padding:0 12px;border:none;background:transparent;color:var(--myhome-snack-action);font:inherit;font-weight:500;cursor:pointer}.pending-bar{z-index:30;background:var(--myhome-card);border:1px solid var(--myhome-divider);border-radius:28px;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.pending-bar .count{font-size:14px}.pending-bar .locked{font-size:13px;color:var(--myhome-warning-ink);flex-basis:100%}.pending-bar button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.pending-bar .discard{padding:0 12px;background:transparent;color:var(--myhome-text-soft)}.pending-bar .review{padding:0 20px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.pending-bar button[disabled]{color:var(--myhome-text-off);background:var(--myhome-background-soft);cursor:default}@media(max-width:599px){.strip.pending-bar{left:8px;right:8px;transform:none;max-width:none;justify-content:space-between}.strip.pending-bar .count{flex-basis:100%}}`,ai=(n,i)=>s`<div class="strip drop-zone ${i?"over":""}" data-group="none">
    ${n.t("panel.assign.drop_zone")}
  </div>`,li=(n,i,e)=>s`<div class="strip dark armed" role="status">
    <span class="what" title=${i}>${n.t("panel.assign.armed",{cover:i})}</span>
    <button type="button" @click=${e}>${n.t("panel.common.action.cancel")}</button>
  </div>`,pi=n=>{let{i18n:i}=n;return s`<div class="strip pending-bar">
    <span class="count"
      >${n.count===1?i.t("panel.assign.pending.count_one"):i.t("panel.assign.pending.count",{count:n.count})}</span
    >
    <button class="discard" type="button" @click=${n.onDiscard}>
      ${i.t("panel.assign.action.discard_all")}
    </button>
    <button
      class="review"
      type="button"
      ?disabled=${n.locked}
      title=${i.t("panel.assign.action.review_hint")}
      @click=${n.onReview}
    >
      ${i.t("panel.assign.action.review")}
    </button>
    ${n.locked?s`<span class="locked"
          >${i.t("panel.banner.measuring.body",{cover:n.lockedCover})}</span
        >`:l}
  </div>`},Te=n=>s`<div class="strip dark applying" role="status">
    ${n.t("panel.banner.applying.title")}
    <span class="under">${n.t("panel.banner.applying.body")}</span>
  </div>`,Ce=(n,i,e)=>s`<div class="strip dark snack" role="status">
    <span>${i}</span>
    ${e?s`<button type="button" @click=${e}>
          ${n.t("panel.toast.action.undo")}
        </button>`:l}
  </div>`;var di=n=>{let i=new Map;for(let e of n.querySelectorAll("[data-row]")){let t=e.getBoundingClientRect();i.set(e.getAttribute("data-row")??"",{top:t.top,left:t.left})}return i},ci=(n,i)=>{if(!tn())for(let e of n.querySelectorAll("[data-row]")){let t=i.get(e.getAttribute("data-row")??"");if(!t)continue;let r=e.getBoundingClientRect(),o=t.left-r.left,a=t.top-r.top;if(Math.abs(o)<1&&Math.abs(a)<1)continue;e.style.transition="none",e.style.transform=`translate(${o}px, ${a}px)`,e.offsetHeight,e.style.transition="transform 220ms ease",e.style.transform="";let p=()=>{e.style.transition="",e.removeEventListener("transitionend",p)};e.addEventListener("transitionend",p)}},tn=()=>typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches;var Ae=class{constructor(i){this._start=null;this._longPress=null;this._pressedAt=null;this._ghost=null;this._target=null;this._scroll=null;this._edge=0;this._scroller=null;this._clearLongPressOnce=()=>this._clearLongPress();this._onPressMove=i=>{let e=this._pressedAt;e&&Math.hypot(i.clientX-e.x,i.clientY-e.y)<12||this._clearLongPress()};this._onMove=i=>{let e=this._start;if(!e)return;if(!e.live){if(Math.hypot(i.clientX-e.x,i.clientY-e.y)<6)return;e.live=!0,this._callbacks.onStart(e.cover)}this._moveGhost(i.clientX,i.clientY),this._autoScroll(i.clientX,i.clientY);let t=this._targetAt(i.clientX,i.clientY,e.cover);nn(t,this._target)||(this._target=t,this._callbacks.onOver(t))};this._onUp=()=>this._finish(!0);this._onCancel=()=>this._finish(!1);this._callbacks=i}get dragging(){return this._start?.live?this._start.cover:null}press(i,e){if(!this._callbacks.blocked()){if(this._callbacks.narrow()){this._arm(i,e);return}e.preventDefault(),this._start={cover:i,x:e.clientX,y:e.clientY,live:!1},window.addEventListener("pointermove",this._onMove),window.addEventListener("pointerup",this._onUp),window.addEventListener("pointercancel",this._onCancel),window.addEventListener("blur",this._onCancel)}}arm(i,e){this._callbacks.blocked()||this._arm(i,e)}cancel(){if(this._start?.live){this._finish(!1);return}this._clear()}stop(){this._clear(),this._clearLongPress()}_arm(i,e){this._clearLongPress(),this._pressedAt=e?{x:e.clientX,y:e.clientY}:null,this._longPress=setTimeout(()=>{this._longPress=null,this._callbacks.onArm(i)},450),window.addEventListener("pointerup",this._clearLongPressOnce),window.addEventListener("pointermove",this._onPressMove),window.addEventListener("pointercancel",this._clearLongPressOnce),window.addEventListener("blur",this._clearLongPressOnce)}_clearLongPress(){this._longPress&&(clearTimeout(this._longPress),this._longPress=null),this._pressedAt=null,window.removeEventListener("pointerup",this._clearLongPressOnce),window.removeEventListener("pointermove",this._onPressMove),window.removeEventListener("pointercancel",this._clearLongPressOnce),window.removeEventListener("blur",this._clearLongPressOnce)}_finish(i){let e=this._start?.live??!1;this._clear(),e&&this._callbacks.onEnd(i)}_clear(){window.removeEventListener("pointermove",this._onMove),window.removeEventListener("pointerup",this._onUp),window.removeEventListener("pointercancel",this._onCancel),window.removeEventListener("blur",this._onCancel),this._start=null,this._target=null,this._stopScrolling(),this._ghost?.remove(),this._ghost=null}ghost(i,e){let t=document.createElement("div");t.className="drag-ghost",t.setAttribute("aria-hidden","true"),t.textContent=i,e.appendChild(t),this._ghost=t}_moveGhost(i,e){this._ghost&&(this._ghost.style.transform=`translate(${i+12}px, ${e+8}px)`)}_autoScroll(i,e){let t=this._callbacks.root().querySelector(".groups");if(!t||t.scrollWidth<=t.clientWidth){this._stopScrolling();return}let r=t.getBoundingClientRect(),o=i<r.left+64?-1:i>r.right-64?1:0;if(this._edge=o,this._scroller=t,o===0){this._stopScrolling();return}if(this._scroll===null){let a=()=>{this._edge===0||!this._scroller||(this._scroller.scrollLeft+=this._edge*14,this._scroll=requestAnimationFrame(a))};this._scroll=requestAnimationFrame(a)}}_stopScrolling(){this._edge=0,this._scroll!==null&&(cancelAnimationFrame(this._scroll),this._scroll=null)}_targetAt(i,e,t){let r=this._callbacks.root().elementFromPoint(i,e),o=r?.closest?.("[data-group]");if(!o)return null;let a=o.getAttribute("data-group")??"",p=r?.closest?.("[data-row]"),d=p?.getAttribute("data-row")??null;if(!p||!d||d===t)return{group:a,beforeId:null,afterId:null,end:!0};let c=p.getBoundingClientRect();return e<c.top+c.height/2?{group:a,beforeId:d,afterId:null,end:!1}:{group:a,beforeId:null,afterId:d,end:!1}}},nn=(n,i)=>n===null||i===null?n===i:n.group===i.group&&n.beforeId===i.beforeId&&n.afterId===i.afterId;var Ie=u`.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;background:var(--myhome-background-soft);color:var(--myhome-text-soft-ink)}.chip.measured{background:var(--myhome-primary-pastel);color:var(--myhome-text)}.chip.adjusted{background:var(--myhome-accent-pastel);color:var(--myhome-text)}.chip .dot{width:6px;height:6px;border-radius:3px;background:var(--myhome-accent);display:inline-block}`,Me=(n,i,e,t)=>{let r=i==="measured"?"measured":i==="adjusted"?"adjusted":"neutral",o;return t&&i==="inherited"?o=n.t("panel.overview.cover.origin_inherited"):t&&i==="adjusted"?o=n.t("panel.overview.cover.origin_adjusted"):o=n.origin(i,e),s`<span class="chip ${r}"
    >${r==="adjusted"?s`<span class="dot" aria-hidden="true"></span>`:l}${o}</span
  >`};var hi=u`.row{position:relative;display:flex;align-items:flex-start;gap:8px;padding:8px;border-radius:8px;min-height:48px;-webkit-user-select:none;-webkit-touch-callout:none}.row .divider{position:absolute;left:8px;right:8px;top:-1px;height:1px;background:var(--myhome-divider);opacity:.6;pointer-events:none}.row .insert-line{position:absolute;left:8px;right:8px;top:-2px;height:3px;border-radius:2px;background:var(--myhome-primary-ink);pointer-events:none}.row .pending-outline{position:absolute;inset:0;border:2px dashed var(--myhome-primary-ink);border-radius:8px;pointer-events:none}.row .source-veil{position:absolute;inset:0;background:var(--myhome-background-soft);opacity:.7;border-radius:8px;pointer-events:none}.row .handle{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);cursor:grab;font-size:18px;letter-spacing:2px;border-radius:8px;touch-action:none;-webkit-user-select:none;user-select:none}.row .handle[disabled]{cursor:default;color:var(--myhome-text-off)}@media(max-width:599px){.row .handle{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.row .handle:focus-visible{position:static;width:48px;height:48px;margin:0;overflow:visible;clip-path:none}}.row .body{flex:1 1 auto;min-width:0}.row .main{display:block;width:100%;text-align:left;border:none;background:transparent;color:inherit;font:inherit;cursor:pointer;padding:2px 0;border-radius:6px}.row .name{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:14.5px;line-height:1.35}.row .sub{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.row .chips:empty{display:none}.row .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}.row .warn{display:block;font-size:12.5px;color:var(--myhome-warning-ink);margin-top:4px}.route{display:inline-flex;align-items:center;gap:2px;font-size:12px;color:var(--myhome-primary-ink);background:var(--myhome-primary-faint);border:1px dashed var(--myhome-primary-ink);border-radius:10px;padding:2px 2px 2px 8px;max-width:100%}.route .text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.route .withdraw{width:48px;height:48px;margin:-14px -14px -14px 0;display:inline-flex;align-items:center;justify-content:center;border:none;background:transparent;color:inherit;font:inherit;font-size:14px;line-height:1;cursor:pointer;border-radius:24px}.row .note{display:block;font-size:12.5px;color:var(--myhome-info-ink);margin-top:4px}`,rn=(n,i,e)=>{let t=i.height!==null?n.t("panel.overview.cover.travel",{travel:n.number(i.height,0)}):e?n.t("panel.overview.cover.travel_needed"):n.t("panel.overview.cover.travel_unknown");return i.area?`${i.area} · ${t}`:t},on=(n,i)=>i.has_own.length===0?"":L.every(e=>i.has_own.includes(e))?n.t("panel.assign.pending.all_own"):n.t("panel.assign.pending.some_own"),ui=(n,i)=>{let{i18n:e,pending:t}=i,r=!!t&&t.to!==null&&n.height===null,o=t?on(e,n):"",a=`chips-${n.unique_id}`;return s`<div class="row" data-row=${n.unique_id}>
    ${i.insertBefore?s`<div class="insert-line" aria-hidden="true"></div>`:i.first?l:s`<div class="divider" aria-hidden="true"></div>`}
    ${t?s`<div class="pending-outline" aria-hidden="true"></div>`:l}
    ${i.dragging?s`<div class="source-veil" aria-hidden="true"></div>`:l}
    <button
      class="handle"
      type="button"
      ?disabled=${i.locked}
      aria-label=${e.t("panel.assign.handle",{cover:n.name})}
      title=${i.locked?e.t("panel.banner.measuring.title"):e.t("panel.assign.handle_hint")}
      @pointerdown=${p=>i.onGrab(n,p)}
      @click=${p=>p.stopPropagation()}
      @keydown=${p=>{(p.key==="Enter"||p.key===" ")&&(p.preventDefault(),i.locked||i.onPick(n))}}
    >
      ⠿
    </button>
    <div
      class="body"
      @pointerdown=${p=>i.onRowPress(n,p)}
    >
      <button class="main" type="button" title=${n.name} aria-describedby=${a}
        @click=${()=>i.onOpen(n)}>
        <span class="name">${n.name}</span>
        <span class="sub">${rn(e,n,r)}</span>
        ${o?s`<span class="note">${o}</span>`:l}
        ${n.profile_missing?s`<span class="warn"
              >${e.t("panel.overview.cover.profile_missing",{profile:n.profile??""})}</span
            >`:l}
        ${n.profile_from_file&&!n.profile_missing?s`<span class="sub">${e.t("panel.overview.cover.from_file")}</span>`:l}
      </button>
      <div class="chips" id=${a}>
        ${Me(e,n.origin,n.profile,i.short)}
        ${t?s`<span class="route">
              <span class="text">${i.route}</span>
              <button
                class="withdraw"
                type="button"
                aria-label=${e.t("panel.assign.action.withdraw")}
                title=${e.t("panel.assign.action.withdraw")}
                @pointerdown=${p=>p.stopPropagation()}
                @click=${()=>i.onWithdraw(n)}
              >
                ✕
              </button>
            </span>`:l}
      </div>
    </div>
  </div>`};var mi=u`.backdrop{position:fixed;inset:0;background:#0006;z-index:60}.dialog{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(440px,92vw);max-height:80vh;overflow:auto;background:var(--myhome-card);color:var(--myhome-text);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);z-index:61;padding:20px;box-sizing:border-box}.dialog h2{margin:0 0 4px;font-size:18px;font-weight:500}.dialog .subtitle{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft)}.dialog .options{display:flex;flex-direction:column;gap:8px}.dialog .option{text-align:left;border-radius:8px;font:inherit;padding:12px;min-height:48px;cursor:pointer;border:1px solid var(--myhome-field-border);background:transparent;color:inherit}.dialog .option.current{border-color:var(--myhome-primary-ink);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.dialog .option .line{display:flex;align-items:baseline;gap:8px}.dialog .option .title{font-weight:500;flex:1}.dialog .option .tag{font-size:12.5px;color:var(--myhome-primary-ink)}.dialog .option .meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.dialog .foot{display:flex;justify-content:flex-end;margin-top:12px}.dialog .foot button{min-height:44px;padding:0 16px;border:none;background:transparent;color:var(--myhome-text-soft);font:inherit;font-size:14px;cursor:pointer}`,sn=(n,i)=>i.missing||i.values.opening_time===void 0?n.t("panel.overview.group.values_unknown"):n.t("panel.dialog.option.profile_meta",{travel:i.reference_height===null?"?":n.number(i.reference_height,0),opening:n.number(i.values.opening_time,1),closing:n.number(i.values.closing_time,1)}),vi=n=>{let{i18n:i}=n,e=(t,r,o)=>s`<button
    class="option ${n.current===t?"current":""}"
    type="button"
    aria-current=${n.current===t?"true":l}
    @click=${()=>n.onPick(t)}
  >
    <span class="line"
      ><span class="title">${r}</span
      >${n.current===t?s`<span class="tag">${i.t("panel.dialog.option.current")}</span>`:l}</span
    >
    <span class="meta">${o}</span>
  </button>`;return s`
    <div class="backdrop" aria-hidden="true" @click=${n.onClose}></div>
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      data-focus-root
    >
      <h2 id="dialog-title">${i.t("panel.dialog.title")}</h2>
      <p class="subtitle">
        ${i.t("panel.dialog.subtitle",{cover:n.cover.name})}
      </p>
      <div class="options">
        ${n.profiles.map(t=>e(t.name,i.t("panel.dialog.option.profile",{profile:t.name}),sn(i,t)))}
        ${e(null,i.t("panel.dialog.option.none"),i.t("panel.dialog.option.none_meta"))}
      </div>
      <div class="foot">
        <button type="button" @click=${n.onClose}>
          ${i.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `};var gi=u`.groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(300px,1fr);gap:16px;align-items:start;overflow-x:auto;padding-bottom:8px;overscroll-behavior-x:contain}}.group{position:relative;background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.group-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider)}.group-head .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.group-head h2{margin:0;font-size:17px;font-weight:500;flex:1 1 auto;min-width:0}.group-head h2 button{border:none;background:transparent;color:var(--myhome-primary-ink);font:inherit;cursor:pointer;padding:0;min-height:28px;text-align:left}.group-head .count{color:var(--myhome-text-soft);font-size:13px}.group-head .meta{margin:6px 0 0;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}.group-head .meta.second{margin-top:4px}.group-head .meta.warn{color:var(--myhome-warning-ink)}.group-body{display:flex;flex-direction:column;padding:8px;gap:2px;min-height:56px}.group-body .empty{margin:8px;font-size:13px;color:var(--myhome-text-soft)}.group-body .insert-end{margin:0 8px;height:3px;border-radius:2px;background:var(--myhome-primary-ink);pointer-events:none}.group .over,.group .armed-target{position:absolute;inset:0;border-radius:var(--myhome-radius);pointer-events:none}.group .over{border:2px solid var(--myhome-primary-ink)}.group .armed-target{border:2px dashed var(--myhome-primary-ink)}.group.collapsed .group-head{border-bottom:none;min-height:48px;cursor:pointer}`,st=n=>n===null?"none":`profile:${n}`,fi=n=>n==="none"?null:n.slice(8),_i=(n,i)=>{let{i18n:e}=i,t=n.covers.length===1?e.t("panel.overview.group.count_one"):e.t("panel.overview.group.count",{count:n.covers.length}),r=i.collapsed;return s`<section
    class="group ${r?"collapsed":""}"
    data-group=${st(n.key)}
    aria-labelledby=${n.id}
  >
    <div
      class="group-head"
      @click=${()=>{r&&i.onTarget(n.key)}}
    >
      <div class="line">
        <h2 id=${n.id}>
          ${n.key===null?n.title:s`<button
                type="button"
                title=${r?e.t("panel.assign.armed",{cover:""}):e.t("panel.overview.group.open")}
                @click=${o=>{if(o.stopPropagation(),r){i.onTarget(n.key);return}i.onOpenProfile(n.key)}}
              >
                ${n.title}
              </button>`}
        </h2>
        <span class="count">${t}</span>
      </div>
      ${n.values&&!r?s`<p class="meta">${n.values}</p>`:l}
      ${r?l:n.warning?s`<p class="meta second warn">${n.warning}</p>`:n.provenance?s`<p class="meta second">${n.provenance}</p>`:l}
    </div>
    ${r?l:s`<div class="group-body">
          ${n.covers.map((o,a)=>ui(o,{i18n:e,short:o.profile===n.key,first:a===0,pending:i.pending.find(p=>p.cover===o.unique_id),route:i.route(o),locked:i.locked,insertBefore:i.insertBefore===o.unique_id,dragging:i.dragging===o.unique_id,onOpen:i.onOpenCover,onGrab:i.onGrab,onRowPress:i.onRowPress,onPick:i.onPick,onWithdraw:i.onWithdraw}))}
          ${i.insertEnd?s`<div class="insert-end" aria-hidden="true"></div>`:l}
          ${n.covers.length===0?s`<p class="empty">${e.t("panel.overview.group.empty")}</p>`:l}
        </div>`}
    ${i.over?s`<div class="over" aria-hidden="true"></div>`:l}
    ${r?s`<div class="armed-target" aria-hidden="true"></div>`:l}
  </section>`};var bi=u`.sheet-backdrop{position:fixed;inset:0;background:#0006;z-index:50}.sheet{position:fixed;left:0;right:0;bottom:0;max-height:86vh;background:var(--myhome-card);color:var(--myhome-text);z-index:51;border-radius:16px 16px 0 0;box-shadow:var(--myhome-shadow);display:flex;flex-direction:column}@media(min-width:600px){.sheet{inset:0 0 0 auto;width:min(480px,100vw);max-height:none;border-radius:0}}.sheet .head{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--myhome-divider)}.sheet .head h2{margin:0;font-size:18px;font-weight:500;flex:1}.sheet .head button{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);font-size:20px;cursor:pointer;border-radius:24px}.sheet .body[aria-busy=true] table,.sheet .body[aria-busy=true] .note{opacity:.55;transition:opacity .12s ease}.sheet .body{flex:1;overflow:auto;padding:16px}.sheet .intro{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .travel-note{background:var(--myhome-info-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}.sheet .travel-note strong{font-weight:500;display:block;margin-bottom:4px}.sheet .item{border:1px solid var(--myhome-divider);border-radius:8px;padding:12px;margin:0 0 12px}.sheet .item .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.sheet .item .name{font-weight:500;flex:1 1 auto;min-width:0}.sheet .item .route{font-size:13px;color:var(--myhome-text-soft)}.sheet label.travel{display:flex;align-items:center;gap:8px;margin:10px 0 2px;font-size:13.5px}.sheet label.travel .what{flex:1}.sheet label.travel input{width:96px;height:44px;border-radius:8px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:inherit;padding:0 10px;font:inherit;font-size:14px;text-align:right}.sheet label.travel input[aria-invalid=true]{border-color:var(--myhome-error-ink)}.sheet .field-error{margin:2px 0 0;font-size:12.5px;color:var(--myhome-error-ink);text-align:right}.sheet table{width:100%;border-collapse:collapse;margin:10px 0 0;font-size:13.5px}.sheet th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}.sheet th.what{text-align:left}.sheet th.after{font-weight:500;color:var(--myhome-text)}.sheet td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}.sheet td.what{text-align:left;color:var(--myhome-text-soft)}.sheet td.after{font-weight:500}.sheet .note{margin:10px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .problem{margin:10px 0 0;font-size:12.5px;color:var(--myhome-error-ink);line-height:1.5}.sheet .show-all{border:none;background:transparent;color:var(--myhome-primary-ink);font:inherit;font-size:13.5px;cursor:pointer;padding:4px 0;min-height:44px}.sheet .refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 12px;font-size:13.5px;line-height:1.5}.sheet .foot{padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));border-top:1px solid var(--myhome-divider);display:flex;gap:12px;justify-content:flex-end}.sheet .foot button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.sheet .foot .back{padding:0 16px;background:transparent;color:var(--myhome-text-soft)}.sheet .foot .confirm{padding:0 24px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.sheet .foot .confirm[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}`,an=(n,i,e,t,r)=>{if(L.every(a=>i.has_own.includes(a)))return n.t("panel.review.note.all_own");if(i.has_own.length>0)return n.t("panel.review.note.some_own");if(e.to===null)return t?.origin==="from_the_file"?n.t("panel.review.note.back_to_file"):n.t("panel.review.note.back_to_defaults");let o=r.get(e.to);return!t||t.height===null||!o||o.reference_height===null?"":n.t("panel.review.note.scaled",{profile:e.to,reference:n.number(o.reference_height,0),travel:n.number(t.height,0)})},wi=(n,i,e,t)=>n.refusal(e,{cover:i.name,covers:i.name,count:1,profile:t.to??"",key:n.t("panel.review.travel.label"),min:20,max:500}),yi=n=>{let{i18n:i}=n,e=new Map((n.preview??[]).map(p=>[p.cover_unique_id,p])),t=n.pending.map(p=>({change:p,cover:n.covers.get(p.cover)})).filter(p=>p.cover!==void 0),r=t.filter(({change:p,cover:d})=>p.to!==null&&d.height===null&&ie(n.heights[p.cover])!==null).length,o=n.showAll?[...ne,...fe]:ne,a=p=>i.t(`options.step.calibration_edit.data.${p}`);return s`
    <!--
      While the batch is in the air every way out is inert, the backdrop and the ✕
      included: Escape is already guarded, and a panel that could be dismissed by a stray
      click on the dark half would take the refusal - and the pending changes it is about
      to show again - off the screen with it.
    -->
    <div
      class="sheet-backdrop"
      aria-hidden="true"
      @click=${()=>{n.applying||n.onClose()}}
    ></div>
    <!--
      A div and not an aside: an aside is a complementary landmark, and a landmark that
      also carries role="dialog" is an element claiming to be two things at once. The
      geometry is the sheet class either way.
    -->
    <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="review-title" data-focus-root>
      <div class="head">
        <h2 id="review-title">${i.t("panel.review.title")}</h2>
        <button
          type="button"
          aria-label=${i.t("panel.common.action.close")}
          ?disabled=${n.applying}
          @click=${n.onClose}
        >
          ✕
        </button>
      </div>
      <div class="body" aria-busy=${n.previewing?"true":"false"}>
        <p class="intro">${i.t("panel.review.intro")}</p>
        ${n.refusal?s`<div class="refusal" role="alert">${n.refusal}</div>`:l}
        ${r>0?s`<div class="travel-note">
              <strong>${i.t("panel.review.travel.title")}</strong>
              ${i.t("panel.review.travel.hint")}
            </div>`:l}
        ${t.map(({change:p,cover:d})=>{let c=e.get(p.cover),m=n.heights[p.cover],h=p.to!==null&&d.height===null,v=h?ie(m):null,_=v!==null&&(n.forced||(m??"")!==""),H=c&&c.problem===null?o.filter(w=>c.values[w]!==void 0&&d.values[w]!==void 0):[];return s`<section class="item">
            <div class="line">
              <span class="name">${d.name}</span>
              <span class="route">${n.route(d)}</span>
            </div>
            ${h?s`<label class="travel">
                    <span class="what">${i.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${m??""}
                      ?disabled=${n.applying}
                      aria-label=${i.t("panel.review.travel.aria")}
                      aria-invalid=${_?"true":"false"}
                      placeholder=${i.t("panel.review.travel.placeholder")}
                      @input=${w=>n.onHeight(p.cover,w.target.value)}
                    />
                    <span>${i.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${_?s`<p class="field-error">
                        ${v==="missing_travel"?i.t("panel.review.travel.required"):wi(i,d,v,p)}
                      </p>`:l}`:l}
            ${c&&c.problem!==null&&c.problem!=="missing_travel"?s`<p class="problem">
                  ${wi(i,d,c.problem,p)}
                </p>`:l}
            ${H.length>0?s`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${i.t("panel.review.before")}</th>
                      <th class="after">${i.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${H.map(w=>s`<tr>
                        <td class="what">${a(w)}</td>
                        <td>${i.number(d.values[w],$[w]??1)}</td>
                        <td class="after">
                          ${i.number(c.values[w],$[w]??1)}
                        </td>
                      </tr>`)}
                  </tbody>
                </table>`:l}
            ${(()=>{let w=an(i,d,p,c,n.profiles);return w?s`<p class="note">${w}</p>`:l})()}
          </section>`})}
        <button class="show-all" type="button" @click=${n.onToggleShowAll}>
          ${n.showAll?i.t("panel.common.action.hide_all"):i.t("panel.common.action.show_all")}
        </button>
      </div>
      <div class="foot">
        <button class="back" type="button" ?disabled=${n.applying} @click=${n.onClose}>
          ${i.t("panel.review.action.back")}
        </button>
        <button
          class="confirm"
          type="button"
          ?disabled=${n.applying||n.forced&&r>0}
          @click=${n.onConfirm}
        >
          ${n.applying?i.t("panel.banner.applying.title"):r>0?r===1?i.t("panel.review.action.missing_travel_one"):i.t("panel.review.action.missing_travel",{count:r}):t.length===1?i.t("panel.review.action.confirm_one"):i.t("panel.review.action.confirm",{count:t.length})}
        </button>
      </div>
    </div>
  `};var Le=class extends f{constructor(){super();this._trap=new $e;this._returnTo=null;this._returnToRow=null;this._onKey=e=>{if(e.key==="Escape"){if(this.state.drag){this._drag.cancel();return}if(this.state.armed){this.actions.arm(null);return}if(this.state.dialog){this.actions.dialog(null);return}this.state.review&&!this.state.applying&&this.actions.review(!1)}};this._flip=null;this._narrowQuery=typeof matchMedia=="function"?matchMedia("(max-width: 599px)"):null;this._onWidth=()=>this.requestUpdate();this._route=e=>{let t=ge(e.unique_id,this.state.pending);return t?this.i18n.t("panel.assign.pending.route",{from:this._groupName(e.profile??null),to:this._groupName(t.to)}):""};this._onGrab=(e,t)=>{this._drag.press(e.unique_id,t)};this._onRowPress=(e,t)=>{this._narrow&&!this._locked&&this._drag.arm(e.unique_id,t)};this.i18n=new y,this.state=U({view:"overview",params:{},path:"/"}),this.actions={},this._drag=new Ae({root:()=>this.renderRoot,blocked:()=>this._locked,narrow:()=>this._narrow,onArm:e=>{let t=this._cover(e);t&&this.actions.arm(t)},onStart:e=>{let t=this._cover(e);t&&(this._drag.ghost(t.name,this.renderRoot),this.actions.drag(t))},onOver:e=>this.actions.over(e),onEnd:e=>this._endDrag(e)})}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[E,P,S,D,Ie,hi,gi,Se,mi,bi,u`:host{display:block;background:transparent}.intro{margin:8px 0 4px;max-width:72ch}.intro p{margin:0 0 8px;line-height:1.55}.counts{margin:0 0 16px;color:var(--myhome-text-soft)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.controls .search{flex:1 1 220px;max-width:340px}.controls .spacer{flex:1 1 auto}.select-wrap{position:relative;display:inline-flex}.select-wrap:after{content:"";position:absolute;right:13px;top:50%;width:7px;height:7px;border-right:1.6px solid var(--myhome-text-soft);border-bottom:1.6px solid var(--myhome-text-soft);border-radius:1px;transform:translateY(-70%) rotate(45deg);pointer-events:none}select.field{appearance:none;padding-right:36px}a.cta{display:inline-flex;align-items:center;text-decoration:none}.welcome{max-width:640px;margin:48px auto;padding:32px}.welcome h2{margin:0 0 12px;font-size:22px;font-weight:500}.welcome p{margin:0 0 8px;line-height:1.55}.welcome .soft{color:var(--myhome-text-soft);margin-bottom:24px}.welcome .after{margin:12px 0 0;font-size:13px;color:var(--myhome-text-soft)}.notice{padding:16px;margin:16px 0;font-size:14px;line-height:1.55}.notice .actions{margin-top:12px}.groups{margin-bottom:96px}.groups.armed{margin-bottom:120px}.drag-ghost{position:fixed;left:0;top:0;z-index:80;pointer-events:none;background:var(--myhome-card);color:var(--myhome-text);border:1px solid var(--myhome-primary-ink);border-radius:8px;box-shadow:var(--myhome-shadow);padding:10px 14px;font-size:14px;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}`]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey),this._narrowQuery?.addEventListener("change",this._onWidth)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._narrowQuery?.removeEventListener("change",this._onWidth),this._drag.stop(),this._trap.release()}updated(e){if(this._locked){let t=this._drag.dragging!==null;this._drag.stop(),t&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"))}if(e.has("state")){let t=e.get("state");if(this._manageFocus(t),this._flip){let r=this._flip;this._flip=null,requestAnimationFrame(()=>ci(this.renderRoot,r))}}}_beforeMove(){this._flip=di(this.renderRoot)}_manageFocus(e){let t=this.state.dialog!==null||this.state.review,r=(e?.dialog??null)!==null||(e?.review??!1);if(t&&!r){let o=this._activeElement();this._returnTo=o,this._returnToRow=o?.closest("[data-row]")?.getAttribute("data-row")??null,requestAnimationFrame(()=>{let a=this.renderRoot.querySelector("[data-focus-root]");a&&this._trap.hold(a)});return}if(!t&&r){this._trap.release();let o=this._returnTo,a=this._returnToRow;this._returnTo=null,this._returnToRow=null,requestAnimationFrame(()=>{((a?[...this.renderRoot.querySelectorAll("[data-row]")].find(c=>c.getAttribute("data-row")===a)?.querySelector(".handle"):null)??(o?.isConnected?o:null))?.focus()})}}_activeElement(){let e=this.renderRoot.activeElement;return e instanceof HTMLElement?e:null}get _overview(){return this.state.overview}get _locked(){return this._overview?.measuring!=null||this.state.applying}get _narrow(){return this._narrowQuery?.matches??!1}_cover(e){return this._overview?.covers.find(t=>t.unique_id===e)}get _covers(){let e=this._overview;return e?jt(e,this.state.order):[]}get _rooms(){let e=new Set;for(let t of this._overview?.covers??[])t.area&&e.add(t.area);return Array.from(e).sort((t,r)=>t.localeCompare(r,this.i18n.language))}_matches(e){let t=this.state.search.trim().toLowerCase();return t&&!e.name.toLowerCase().includes(t)?!1:!this.state.room||e.area===this.state.room}_groupName(e){return e===null?this.i18n.t("panel.overview.group.no_profile"):this.i18n.t("panel.overview.group.profile",{profile:e})}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group.values_unknown"):this.i18n.t("panel.overview.group.values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),opening:this.i18n.number(e.values.opening_time,1),closing:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml")return this.i18n.t("panel.overview.group.from_file");if(!e.measured_on)return this.i18n.t("panel.overview.group.provenance_missing");let t=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.group.measured_on_gone",{date:t});let r=this.i18n.t("panel.overview.group.measured_on",{cover:e.measured_on_name,date:t}),o=(this._overview?.covers??[]).find(a=>a.unique_id===e.measured_on);if(o&&o.profile!==e.name){let a=o.profile??this.i18n.t("panel.overview.group.no_profile");r+=` · ${this.i18n.t("panel.profile.provenance_now_profile",{profile:a})}`}return r}get _groups(){let e=this._overview;if(!e)return[];let t=this._covers,r=a=>t.filter(p=>ve(p,this.state.pending)===a&&this._matches(p)),o=e.profiles.map((a,p)=>({key:a.name,id:`group-${p}`,title:this.i18n.t("panel.overview.group.profile",{profile:a.name}),values:this._valuesLine(a),provenance:this._provenanceLine(a),warning:a.missing?this.i18n.t("panel.overview.group.missing"):"",covers:r(a.name)}));return o.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group.no_profile"),values:this.i18n.t("panel.overview.group.no_profile_note"),provenance:"",warning:"",covers:r(null)}),o}_appendAtEnd(e,t){if(this.state.order===null||t===(e.profile??null))return;let r=this._covers;this.actions.setOrder(Gt(r.map(o=>o.unique_id),e.unique_id,r.filter(o=>ve(o,this.state.pending)===t).map(o=>o.unique_id)))}_endDrag(e){let t=this.state,r=t.drag,o=r?.insert??null,a=r?.over??null,p=r?this._cover(r.cover):void 0;if(this.actions.drag(null),!e||!p||a===null){r&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));return}let d=fi(a),c=this._covers.map(_=>_.unique_id),m=tt(c,p.unique_id,o??{beforeId:null,afterId:null});this._beforeMove();let h=ge(p.unique_id,t.pending),v=h?h.to:p.profile??null;if(d!==v){this.actions.setOrder(m),this.actions.assign(p,d);return}if(t.pending.length>0){this.actions.setOrder(m),this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));return}this.actions.reorder(m)}_renderControls(){return s`<div class="controls">
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
          ${this._rooms.map(e=>s`<option value=${e}>${e}</option>`)}
        </select>
      </span>
      <span class="spacer"></span>
      <a class="cta secondary compact" href=${R} title=${this.i18n.t("panel.firstrun.note")}
        >${this.i18n.t("panel.firstrun.action.measure")}</a
      >
    </div>`}_renderFirstRun(){return s`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <a class="cta" href=${R}>${this.i18n.t("panel.firstrun.action.measure")}</a>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`}_renderStrips(){let e=this.state;if(e.drag)return ai(this.i18n,e.drag.over==="none");if(e.armed){let t=this._cover(e.armed);return li(this.i18n,t?.name??"",()=>this.actions.arm(null))}return e.applying?Te(this.i18n):e.snack?Ce(this.i18n,e.snack.message,e.snack.undoToken?()=>this.actions.undo():null):e.pending.length>0&&!e.review?pi({i18n:this.i18n,count:e.pending.length,locked:this._locked,lockedCover:this._overview?.measuring?.name??"",onDiscard:()=>{this._beforeMove(),this.actions.discardAll()},onReview:()=>this.actions.review(!0)}):l}_renderDialog(){let e=this.state.dialog?this._cover(this.state.dialog):void 0;return e?vi({i18n:this.i18n,cover:e,profiles:this._overview?.profiles??[],current:ve(e,this.state.pending),onPick:t=>{this._beforeMove(),this._appendAtEnd(e,t),this.actions.assign(e,t)},onClose:()=>this.actions.dialog(null)}):l}_renderReview(){let e=this._overview;return!this.state.review||!e?l:yi({i18n:this.i18n,pending:this.state.pending,covers:new Map(e.covers.map(t=>[t.unique_id,t])),profiles:new Map(e.profiles.map(t=>[t.name,t])),preview:this.state.preview,previewing:this.state.previewing,heights:this.state.heights,forced:this.state.heightsForced,showAll:this.state.showAll,applying:this.state.applying,refusal:this.state.writeError?this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{}):"",route:this._route,onHeight:(t,r)=>this.actions.height(t,r),onToggleShowAll:()=>this.actions.toggleShowAll(),onConfirm:()=>this.actions.confirm(),onClose:()=>this.actions.review(!1)})}render(){let e=this._overview;if(!e)return s`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return s`<section class="card welcome">
        <h2>${this.i18n.t("panel.overview.no_basic_covers_title")}</h2>
        <div>${K(this.i18n.t("panel.overview.no_basic_covers"))}</div>
        <a class="cta secondary" href=${R} title=${this.i18n.t("panel.common.opens_configure")}
          >${this.i18n.t("panel.common.action.configure")}</a
        >
      </section>`;if(e.profiles.length===0)return this._renderFirstRun();let t=this._groups,r=t.reduce((p,d)=>p+d.covers.length,0),o=this.state.search.trim()!==""||this.state.room!=="",a=this.state.drag;return s`
      <div class="intro">${this.i18n.md("panel.overview.explanation")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.summary",{profiles:e.profiles.length,covers:e.covers.length})}
      </p>
      ${this._renderControls()}
      ${r===0&&o?s`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${()=>this.actions.clearFilters()}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`:s`<div class="groups ${this.state.armed!==null?"armed":""}">
            ${t.map(p=>{let d=st(p.key),c=a?.insert??null,m=c!==null&&c.group===d;return _i(p,{i18n:this.i18n,pending:this.state.pending,route:this._route,locked:this._locked,collapsed:this.state.armed!==null,over:a?.over===d,insertBefore:m?c.beforeId:null,insertEnd:m?c.end||c.afterId===p.covers.at(-1)?.unique_id:!1,dragging:a?.cover??null,onOpenProfile:h=>this.actions.openProfile(h),onOpenCover:h=>this.actions.openCover(h.unique_id),onGrab:this._onGrab,onRowPress:this._onRowPress,onPick:h=>this.actions.dialog(h),onWithdraw:h=>{this._beforeMove(),this.actions.withdraw(h)},onTarget:h=>{let v=this.state.armed?this._cover(this.state.armed):void 0;v&&(this._beforeMove(),this._appendAtEnd(v,h),this.actions.assign(v,h))}})})}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",Le);var Oe=u`:host{display:block}.card{padding:16px;margin:0 0 16px;max-width:720px}h2{margin:0 0 4px;font-size:16px;font-weight:500}h2:focus-visible{outline:2px solid var(--myhome-primary-ink);outline-offset:4px}.sub{margin:0;font-size:13px;color:var(--myhome-text-soft)}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}.intro{margin:0 0 12px;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}table[aria-busy=true],.rows[aria-busy=true]{opacity:.55;transition:opacity .12s ease}.rows{display:flex;flex-direction:column}.row{display:flex;align-items:baseline;gap:8px;padding:8px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.row .what{flex:1 1 150px;color:var(--myhome-text-soft)}.row .value{font-variant-numeric:tabular-nums;font-weight:500}.row .from{flex-basis:100%;font-size:12px;color:var(--myhome-text-soft);text-align:right}.row .instead{font-size:12px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}h3{margin:16px 0 4px;font-size:14px;font-weight:500}.actions{display:flex;flex-direction:column;gap:8px}.wide{min-height:48px;border:none;border-radius:8px;background:var(--myhome-primary-faint);color:var(--myhome-primary-ink);font:inherit;font-size:14px;cursor:pointer;text-align:left;padding:10px 14px;display:block;width:100%}.wide.destructive{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}.wide[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.wide .note{display:block;color:var(--myhome-text-soft);font-size:12.5px;margin-top:2px}.warn{background:var(--myhome-warning-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13px;line-height:1.5}.warn strong{font-weight:500;display:block;margin-bottom:4px}.danger{background:var(--myhome-error-pastel);border-radius:8px;padding:16px;font-size:14px;line-height:1.55}.danger strong{font-weight:500}.danger p{margin:8px 0 0}.danger ul{margin:4px 0 0;padding:0 0 0 20px;line-height:1.7}.danger .soft{color:var(--myhome-text-soft);font-size:13px}.fields{display:flex;flex-direction:column;gap:10px}label.field-row{display:flex;align-items:center;gap:8px;font-size:13.5px}label.field-row .what{flex:1}label.field-row input{width:110px;text-align:right}label.field-row .unit{color:var(--myhome-text-soft);width:24px}.field[aria-invalid=true]{border-color:var(--myhome-error-ink)}.field-error{margin:2px 26px 0 0;font-size:12.5px;color:var(--myhome-error-ink);text-align:right}.foot{display:flex;gap:12px;justify-content:flex-end;margin-top:16px}table{width:100%;border-collapse:collapse;margin:16px 0 0;font-size:13.5px}th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}th.what,td.what{text-align:left}th.after{font-weight:500;color:var(--myhome-text)}td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}td.what{color:var(--myhome-text-soft)}td.after{font-weight:500}a{color:var(--myhome-primary-ink)}.refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}`,ae=(n,i,e,t,r)=>s`<div class="row">
  <span class="what">${n}</span>
  <span class="value">${i}${e?s` ${e}`:l}</span>
  ${r?s`<span class="instead">${r}</span>`:l}
  ${t?s`<span class="from">${t}</span>`:l}
</div>`,le=n=>s`<div>
  <label class="field-row">
    <span class="what">${n.label}</span>
    <input
      class="field"
      type="text"
      inputmode="decimal"
      .value=${n.value}
      ?disabled=${n.disabled}
      placeholder=${n.placeholder??""}
      aria-label=${n.ariaLabel??n.label}
      aria-invalid=${n.error?"true":"false"}
      @input=${i=>n.onInput(i.target.value)}
    />
    <span class="unit">${n.unit}</span>
  </label>
  ${n.error?s`<p class="field-error">${n.error}</p>`:l}
</div>`,x=n=>s`<button
  class="wide ${n.destructive?"destructive":""}"
  type="button"
  title=${n.title??""}
  ?disabled=${n.disabled??!1}
  @click=${n.onClick}
>
  ${n.label}
  ${n.note?s`<span class="note">${n.note}</span>`:l}
</button>`,T=(n,i,e,t=!1)=>s`<div class="foot">
  <button class="cta text" type="button" ?disabled=${t} @click=${i}>
    ${n}
  </button>
  ${e}
</div>`;var j=[...ne,...fe],ze=class extends f{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)){if(this.state.detail.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new y,this.state=U({view:"cover",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[E,P,S,D,Ie,Oe,Ee]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.detail,t=`${e.for??""}|${e.mode}`;if(t===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=t,se(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}_label(e){return this.i18n.t(`options.step.calibration_edit.data.${e}`)}_unit(e){let t=_e[e];return t?this.i18n.t(t):""}_number(e,t){return this.i18n.number(t,$[e]??O[e]?.decimals??1)}_problem(e,t){return this.i18n.refusal(t,{key:this._label(e),min:O[e]?.min??0,max:O[e]?.max??0,cover:this.state.detail.answer?.cover.name??""})}_destination(){let e=this.state.detail.answer?.forget;return e?e.falls_back_to==="profile"?this.i18n.t("panel.detail.destination.profile",{profile:e.profile??""}):e.falls_back_to==="file"?this.i18n.t("panel.detail.destination.file"):this.i18n.t("panel.detail.destination.defaults"):""}render(){let e=this.state.detail;return e.loading?Pe(this.i18n):e.answer?s`${this._head(e.answer.cover)}
    ${this.state.writeError?s`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:l}
    ${e.mode==="view"?this._view(e.answer.cover,e.answer.keys):l}
    ${e.mode==="edit"?this._edit(e.answer.keys):l}
    ${e.mode==="travel"?this._travel(e.answer.cover):l}
    ${e.mode==="correct"?this._correct():l}
    ${e.mode==="remove"?this._remove(e.answer.cover):l}`:s`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.unknown")}</h2>
        <p class="sub">
          ${e.error?this.i18n.refusal(e.error.translation_key,e.error.translation_placeholders??{}):""}
        </p>
        ${T(this.i18n.t("panel.common.action.retry"),this.actions.retry,s`<button class="cta secondary compact" type="button" @click=${this.actions.back}>
            ${this.i18n.t("panel.common.action.back")}
          </button>`)}
      </div>`}_head(e){let t=[e.area,e.height===null?this.i18n.t("panel.overview.cover.travel_unknown"):this.i18n.t("panel.overview.cover.travel",{travel:this.i18n.number(e.height,0)}),e.profile?this.i18n.t("panel.overview.cover.follows",{profile:e.profile}):null].filter(o=>!!o),r=e.level==="precise"?this.i18n.t("panel.detail.level_thorough"):e.level==="basic"?this.i18n.t("panel.detail.level_basic"):null;return s`<section class="card">
      <p class="sub">${t.join(" · ")}</p>
      <div class="chips">
        ${Me(this.i18n,e.origin,e.profile,!1)}
        ${e.measured_at?s`<span class="chip"
              >${this.i18n.t("panel.detail.measured_at",{date:this.i18n.date(e.measured_at)})}${r?` · ${r}`:""}</span
            >`:l}
        ${e.verify_note!==null?s`<span class="chip"
              >${this.i18n.t("panel.detail.verify_note",{deviation:this.i18n.number(e.verify_note,1)})}</span
            >`:l}
      </div>
      ${e.profile_missing?s`<p class="warn" style="margin-top:12px;margin-bottom:0">
            ${this.i18n.t("panel.overview.cover.profile_missing",{profile:e.profile??""})}
          </p>`:l}
      ${e.profile_from_file?s`<p class="sub" style="margin-top:8px">
            ${this.i18n.t("panel.overview.cover.from_file")}
          </p>`:l}
    </section>`}_view(e,t){let r=j.map(p=>t.find(d=>d.key===p)).filter(p=>p!==void 0),o=e.has_own.length>0,a=o&&e.level!=="precise";return s`<section class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.values.title")}</h2>
        <p class="intro">${this.i18n.t("panel.detail.values.intro")}</p>
        <div class="rows">
          ${r.map(p=>this._valueRow(e,p))}
        </div>
      </section>
      <section class="card actions">
        ${x({label:this.i18n.t("panel.detail.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
        ${x({label:this.i18n.t("panel.detail.action.travel"),note:this.i18n.t("options.step.calibration_edit.data_description.height"),disabled:this._locked,onClick:()=>this.actions.mode("travel")})}
        ${x({label:this.i18n.t("panel.detail.action.assign"),disabled:this._locked,onClick:this.actions.assign})}
        ${e.profile?x({label:this.i18n.t("panel.overview.group.open"),note:this.i18n.t("panel.overview.group.profile",{profile:e.profile}),onClick:()=>this.actions.openProfile(e.profile)}):l}
        ${this._flowButton("panel.detail.action.measure_again","panel.detail.action.measure_again_note")}
        ${o?x({label:this.i18n.t("panel.detail.action.correct"),note:this.i18n.t("panel.detail.action.correct_note"),onClick:()=>this.actions.mode("correct")}):l}
        ${a?this._flowButton("panel.detail.action.thorough","panel.detail.action.thorough_note"):l}
        ${o?x({label:this.i18n.t("panel.detail.action.remove"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("remove")}):l}
      </section>`}_valueRow(e,t){let r=t.origin==="own"?this.i18n.t("panel.detail.source.own"):t.origin==="profile"?this.i18n.t("panel.detail.source.profile",{profile:e.profile??""}):t.origin==="file"?this.i18n.t("panel.detail.source.file"):this.i18n.t("panel.detail.source.default");return ae(this._label(t.key),this._number(t.key,t.value),this._unit(t.key),r,t.own&&t.inherited_value!==null?this.i18n.t("panel.detail.edit.inherits",{value:this._number(t.key,t.inherited_value)}):null)}_flowButton(e,t){return x({label:`${this.i18n.t(e)} ↗`,note:this.i18n.t(t),title:this.i18n.t("panel.common.opens_configure"),onClick:r=>this.actions.openFlow(r.currentTarget)})}_edit(e){let t=this.state.detail.form,r=j.map(a=>e.find(p=>p.key===a)).filter(a=>a!==void 0),o=r.some(a=>b(a.key,t[a.key])!==null);return s`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.edit.title")}</h2>
      <div class="warn">${this.i18n.t("panel.detail.edit.intro")}</div>
      <div class="fields">
        ${r.map(a=>this._field(a))}
      </div>
      ${T(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),s`<button class="cta compact" type="button" ?disabled=${this._locked||o}
          @click=${this.actions.saveValues}>
          ${this.i18n.t("panel.detail.edit.action.save")}
        </button>`,this.state.applying)}
    </section>`}_field(e){let t=this.state.detail.form[e.key],r=b(e.key,t),o=e.inherited_value===null?this.i18n.t("panel.detail.edit.empty"):this.i18n.t("panel.detail.edit.inherits",{value:this._number(e.key,e.inherited_value)});return le({label:this._label(e.key),value:t??"",unit:this._unit(e.key),placeholder:o,error:r?this._problem(e.key,r):null,disabled:this.state.applying,onInput:a=>this.actions.field(e.key,a)})}_travel(e){let t=this.state.detail.form.height,r=b("height",t),o=this.state.detail.preview,a=o&&o.problem===null?j.filter(p=>o.values[p]!==void 0&&e.values[p]!==void 0):[];return s`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("options.step.calibration_edit.data.height")}
      </h2>
      <p class="intro">
        ${this.i18n.t("options.step.calibration_edit.data_description.height")}
      </p>
      ${le({label:this.i18n.t("panel.review.travel.label"),ariaLabel:this.i18n.t("panel.review.travel.aria"),value:t??"",unit:this.i18n.t("panel.common.unit.centimetres"),placeholder:this.i18n.t("panel.review.travel.placeholder"),error:r?this._problem("height",r):null,disabled:this.state.applying,onInput:p=>this.actions.field("height",p)})}
      ${o&&o.problem!==null?s`<p class="field-error">${this._problem("height",o.problem)}</p>`:l}
      ${a.length>0?s`<table aria-busy=${this.state.detail.previewing?"true":"false"}>
            <thead>
              <tr>
                <th class="what"></th>
                <th>${this.i18n.t("panel.review.before")}</th>
                <th class="after">${this.i18n.t("panel.review.after")}</th>
              </tr>
            </thead>
            <tbody>
              ${a.map(p=>s`<tr>
                  <td class="what">${this._label(p)}</td>
                  <td>${this._number(p,e.values[p])}</td>
                  <td class="after">
                    ${this._number(p,o.values[p])}
                  </td>
                </tr>`)}
            </tbody>
          </table>`:l}
      ${T(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),s`<button class="cta compact" type="button"
          ?disabled=${this._locked||r!==null||k(t)}
          @click=${this.actions.saveTravel}>
          ${this.i18n.t("panel.common.action.save")}
        </button>`,this.state.applying)}
    </section>`}_correct(){return s`<section class="card actions">
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
    </section>`}_remove(e){let t=this.state.detail.answer?.forget;return s`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.remove.title")}</h2>
      <div class="danger">
        <p style="margin:0">
          ${this.i18n.t("panel.detail.remove.body",{cover:e.name,destination:this._destination()})}
        </p>
        ${t?.travel_stays?s`<p class="soft">${this.i18n.t("panel.detail.remove.travel_stays")}</p>`:l}
      </div>
      ${T(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),s`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.detail.remove.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-cover-detail")||customElements.define("myhome-cover-detail",ze);var G=["reference_height",...L],ln=/^[A-Za-z0-9_]+$/,De=class extends f{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)){if(this.state.profile.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new y,this.state=U({view:"profile",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[E,P,S,D,Oe]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.profile,t=`${e.for??""}|${e.mode}`;if(t===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=t,se(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}get _profile(){let e=this.state.profile.for;return this.state.overview?.profiles.find(t=>t.name===e)??null}get _followers(){let e=this._profile,t=this.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return t.filter(o=>r.has(o.unique_id))}_label(e){return e==="reference_height"?this.i18n.t("panel.profile.reference_travel"):this.i18n.t(`options.step.profile_edit.data.${e}`)}_unit(e){let t=_e[e];return t?this.i18n.t(t):""}_number(e,t){return this.i18n.number(t,$[e]??O[e]?.decimals??1)}_problem(e,t){return this.i18n.refusal(t,{key:this._label(e),min:O[e]?.min??0,max:O[e]?.max??0})}_ownKeys(e){return e.has_own.map(t=>this.i18n.t(`options.step.calibration_edit.data.${t}`)).join(", ")}render(){let e=this._profile;if(!this.state.overview)return s`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;if(!e)return s`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.unknown")}</h2>
        ${T(this.i18n.t("panel.common.action.back"),this.actions.back,l)}
      </div>`;let t=this.state.profile.mode;return s`${this._head(e)}
    ${this.state.writeError?s`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:l}
    ${t==="view"?this._view(e):l}
    ${t==="edit"?this._edit():l}
    ${t==="rename"?this._rename(e):l}
    ${t==="delete"?this._delete(e):l}`}_head(e){let r=(this.state.overview?.covers??[]).find(p=>p.unique_id===e.measured_on),o;e.measured_on&&e.measured_on_name&&e.measured_at?(o=this.i18n.t("panel.profile.provenance",{cover:e.measured_on_name,date:this.i18n.date(e.measured_at)}),r&&r.profile!==e.name&&(o+=` · ${r.profile?this.i18n.t("panel.profile.provenance_now_profile",{profile:r.profile}):this.i18n.t("panel.profile.provenance_now_none")}`)):e.measured_on&&e.measured_at?o=this.i18n.t("panel.overview.group.measured_on_gone",{date:this.i18n.date(e.measured_at)}):o=this.i18n.t("panel.profile.provenance_missing");let a=e.editable?this.i18n.t("panel.profile.stored"):this.i18n.t("panel.profile.from_file");return s`<section class="card">
      <p class="sub">${e.missing?o:`${a} · ${o}`}</p>
      ${e.missing?s`<p class="warn" style="margin:12px 0 0">
            ${this.i18n.t("panel.overview.group.values_unknown")}
          </p>`:l}
    </section>`}_view(e){let t=this._followers;return s`${e.missing?l:s`<section class="card">
            <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.values")}</h2>
            <div class="rows">
              ${G.map(r=>r==="reference_height"?e.reference_height===null?l:ae(this._label(r),this._number(r,e.reference_height),this._unit(r),"",null):e.values[r]===void 0?l:ae(this._label(r),this._number(r,e.values[r]),this._unit(r),"",null))}
            </div>
          </section>`}
      <section class="card">
        <h2 ?data-heading=${e.missing} tabindex="-1">
          ${t.length===0?this.i18n.t("panel.profile.followers.none"):t.length===1?this.i18n.t("panel.profile.followers.count_one"):this.i18n.t("panel.profile.followers.count",{count:t.length})}
        </h2>
        <p class="intro">${this.i18n.t("panel.profile.edit.intro")}</p>
        <div class="rows">
          ${t.map(r=>this._follower(r))}
        </div>
      </section>
      ${e.editable?s`<section class="card actions">
            ${x({label:this.i18n.t("panel.profile.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
            ${x({label:this.i18n.t("panel.profile.action.rename"),disabled:this._locked,onClick:()=>this.actions.mode("rename")})}
            ${x({label:this.i18n.t("panel.profile.action.delete"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("delete")})}
          </section>`:l}`}_follower(e){let r=L.every(o=>e.has_own.includes(o))?this.i18n.t("panel.profile.followers.measured"):e.has_own.length>0?this.i18n.t("panel.profile.followers.adjusted",{keys:this._ownKeys(e)}):this.i18n.t("panel.profile.followers.inherited");return s`<div class="row">
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
      <span class="instead">${r}</span>
      ${e.profile_from_file?s`<span class="from">${this.i18n.t("panel.overview.cover.from_file")}</span>`:l}
    </div>`}_edit(){let e=this._followers,t=this.state.profile.form,r=G.some(a=>b(a,t[a])!==null||k(t[a])),o=e.length===1?this.i18n.t("panel.profile.edit.reach_one"):this.i18n.t("panel.profile.edit.reach_all",{count:e.length});return s`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.action.edit")}</h2>
      <div class="warn">
        <strong>${this.i18n.t("panel.profile.edit.reach",{target:o})}</strong>
        ${this.i18n.t("panel.profile.edit.intro")}
      </div>
      <div class="fields">
        ${G.map(a=>le({label:this._label(a),value:t[a]??"",unit:this._unit(a),error:k(t[a])?this.i18n.t("panel.common.required"):(()=>{let p=b(a,t[a]);return p?this._problem(a,p):null})(),disabled:this.state.applying,onInput:p=>this.actions.field(a,p)}))}
      </div>
      <h3>${this.i18n.t("panel.profile.impact.title")}</h3>
      <div class="rows" aria-busy=${this.state.profile.impacting?"true":"false"}>
        ${e.map(a=>this._impact(a,r))}
      </div>
      ${T(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),s`<button class="cta compact" type="button" ?disabled=${this._locked||r}
          @click=${this.actions.saveValues}>
          ${e.length===1?this.i18n.t("panel.profile.edit.action.save_one"):this.i18n.t("panel.profile.edit.action.save",{count:e.length})}
        </button>`,this.state.applying)}
    </section>`}_impact(e,t){let r=L.every(p=>e.has_own.includes(p)),o=r?this.i18n.t("panel.profile.impact.state_measured"):e.has_own.length>0?this.i18n.t("panel.profile.impact.state_adjusted"):this.i18n.t("panel.profile.impact.state_inherited"),a;if(r)a=this.i18n.t("panel.profile.impact.no_change");else if(e.height===null)a=this.i18n.t("panel.profile.impact.no_travel");else if(t)a=this.i18n.t("panel.profile.impact.invalid");else{let p=(this.state.profile.impact??[]).find(d=>d.cover_unique_id===e.unique_id);if(!p||p.problem!==null)a=this.i18n.t("panel.common.loading");else if(a=L.filter(c=>!e.has_own.includes(c)&&e.values[c]!==void 0&&p.values[c]!==void 0).map(c=>`${this.i18n.t(`options.step.calibration_edit.data.${c}`)} ${this._number(c,e.values[c])} → ${this._number(c,p.values[c])}`).join(" · "),e.has_own.length>0){let c=this.i18n.t("panel.profile.impact.kept",{keys:this._ownKeys(e)});a=a?`${a} — ${c}`:c}}return s`<div class="row">
      <span class="what">${e.name}</span>
      <span class="instead">${o}</span>
      <span class="from" style="text-align:left">${a}</span>
    </div>`}_rename(e){let t=this.state.profile.newName,r=t.trim()!==""&&!ln.test(t.trim()),o=r?this.i18n.refusal("invalid_name",{profile:t}):this.state.profile.nameError;return s`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.rename.title")}</h2>
      <p class="intro">${this.i18n.t("panel.profile.rename.rule")}</p>
      <label class="field-row">
        <span class="what">${this.i18n.t("panel.profile.rename.field")}</span>
        <input
          class="field"
          type="text"
          style="width:220px;text-align:left"
          .value=${t}
          ?disabled=${this.state.applying}
          aria-label=${this.i18n.t("panel.profile.rename.field")}
          aria-invalid=${o?"true":"false"}
          @input=${a=>this.actions.newName(a.target.value)}
        />
      </label>
      ${o?s`<p class="field-error" style="text-align:left">${o}</p>`:l}
      ${T(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),s`<button class="cta compact" type="button"
          ?disabled=${this._locked||r||t.trim()===""||t.trim()===e.name}
          @click=${this.actions.rename}>
          ${this.i18n.t("panel.profile.rename.action")}
        </button>`,this.state.applying)}
    </section>`}_delete(e){let t=this._followers;return s`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("panel.profile.delete.title",{profile:e.name})}
      </h2>
      <div class="danger">
        ${t.length===0?s`<p style="margin:0">${this.i18n.t("panel.profile.followers.none")}</p>`:s`<p style="margin:0">${this.i18n.t("panel.profile.delete.affects")}</p>
              <ul>
                ${t.map(r=>s`<li>${r.name}</li>`)}
              </ul>`}
        <p>${this.i18n.t("panel.profile.delete.body")}</p>
      </div>
      ${T(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),s`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.profile.delete.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-profile-card")||customElements.define("myhome-profile-card",De);var xi=(n,i)=>n.summary?.note?s`<div class="stub">${n.summary.note}</div>`:l;var $i=(n,i)=>{let e=n.options??[];return e.length===0?l:s`<div class="options" role="group" aria-label=${n.title}>
    ${e.map(t=>s`<button
        class="option"
        type="button"
        aria-pressed=${t.current?"true":"false"}
        @click=${()=>i.fire(t.action)}
      >
        <span class="option-head">
          <strong class="option-title">${t.title}</strong>
          ${t.chip?s`<span class="chip neutral">${t.chip}</span>`:l}
        </span>
        ${t.meta?s`<span class="option-meta">${t.meta}</span>`:l}
      </button>`)}
  </div>`};var ki=(n,i)=>{let e=n.progress;if(!e)return s`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`;let t=Math.max(0,Math.min(1,e.fraction))*100;return s`<div class="progress-card">
    ${e.text?s`<p class="instruction">${e.text}</p>`:l}
    <div
      class="progress-track"
      role="progressbar"
      aria-label=${e.text||i.i18n.t("panel.screen.progress")}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow=${Math.round(t)}
    >
      <div class="progress-bar" style=${`width:${t}%`}></div>
    </div>
    <p class="progress-eta" role="status">
      ${e.done?i.i18n.t("panel.screen.completed"):e.eta??""}
    </p>
  </div>`};var Ri=(n,i)=>{let e=n.press;if(!e)return s`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`;let t=e.state==="moving";return s`
    ${e.instruction?s`<p class="instruction">${e.instruction}</p>`:l}
    <div class="live">
      <div class="live-row">
        <span class="name">${i.i18n.t("panel.screen.motor")}</span>
        <span class="value ${t?"moving":""}">${e.motor??""}</span>
      </div>
      ${e.position?s`<div class="live-row">
            <span class="name">${i.i18n.t("panel.screen.position")}</span>
            <span class="value">${e.position}</span>
          </div>`:l}
    </div>
    ${e.note?s`<div
          class="note ${e.state==="problem"?"error":"success"}"
          role=${e.state==="problem"?"alert":"status"}
        >
          ${e.note}
        </div>`:l}
  `};var Ei=(n,i)=>{let e=n.options??[];if(e.length===0&&!n.field)return s`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`;let t=n.field;return s`
    <div class="options" role="group" aria-label=${n.title}>
      ${e.map(r=>s`<button
          class="option"
          type="button"
          aria-pressed=${r.current?"true":"false"}
          @click=${()=>i.fire(r.action)}
        >
          <strong class="option-title">${r.title}</strong>
          ${r.meta?s`<span class="option-meta">${r.meta}</span>`:l}
        </button>`)}
    </div>
    ${t?s`<div class="reading" style="margin-top:12px">
          <label for="gap">${t.label}</label>
          <div class="row">
            <input
              id="gap"
              inputmode="decimal"
              .value=${t.value}
              placeholder=${t.placeholder??""}
              aria-describedby=${t.error?"gap-error":l}
              aria-invalid=${t.error?"true":"false"}
              @input=${r=>i.fire("field",r.target.value)}
            />
            ${t.unit?s`<span class="unit">${t.unit}</span>`:l}
          </div>
          ${t.error?s`<p class="error" id="gap-error" role="alert">${t.error}</p>`:l}
        </div>`:l}
  `};var pn=n=>{let i=[n.hint?"reading-hint":"",n.error?"reading-error":""].filter(e=>e!=="");return i.length>0?i.join(" "):void 0},Pi=(n,i)=>{let e=n.field;return e?s`<div class="reading ${e.big===!1?"":"big"}">
    <label for="reading">${e.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${e.value}
        placeholder=${e.placeholder??""}
        aria-describedby=${pn(e)??l}
        aria-invalid=${e.error?"true":"false"}
        @input=${t=>i.fire("field",t.target.value)}
      />
      ${e.unit?s`<span class="unit">${e.unit}</span>`:l}
    </div>
    ${e.hint?s`<p class="hint" id="reading-hint">${e.hint}</p>`:l}
    ${e.error?s`<p class="error" id="reading-error" role="alert">${e.error}</p>`:l}
  </div>`:s`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`};var Si=(n,i)=>{let e=n.summary;return e?s`
    <div class="summary">
      ${e.rows.map(t=>s`<div class="summary-row">
          <span class="label">${t.label}</span>
          ${t.before?s`<span class="before" aria-label=${i.i18n.t("panel.review.before")}
                >${t.before}</span
              >`:l}
          <span class="after" aria-label=${i.i18n.t("panel.review.after")}>${t.after}</span>
        </div>`)}
      ${e.note?s`<p class="note-line">${e.note}</p>`:l}
    </div>
    ${e.code?s`<pre class="code">${e.code}</pre>`:l}
  `:s`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`};var Ti=(n,i)=>n.summary?.rows?.length?s`<div class="summary">
    ${n.summary.rows.map(e=>s`<div class="summary-row">
        <span class="label">${e.label}</span>
        <span class="after">${e.after}</span>
      </div>`)}
    ${n.summary.note?s`<p class="note-line">${n.summary.note}</p>`:l}
  </div>`:l;var Ci=u`.text-column{min-width:0}.phase{margin:0 0 8px;font-size:12px;color:var(--myhome-text-soft)}.new-text{display:inline-block;margin:0 0 12px;background:var(--myhome-info-pastel);border-radius:10px;padding:3px 10px;font-size:12px;color:var(--myhome-text-soft)}.screen-title{margin:0 0 12px;font-size:20px;font-weight:500;line-height:1.3;display:flex;align-items:center;gap:10px}.outcome-icon{width:32px;height:32px;flex:0 0 32px;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;font-weight:600}.outcome-icon.saved{background:var(--myhome-success-pastel);color:var(--myhome-success-ink)}.outcome-icon.saved:before{content:"\2713"}.outcome-icon.cancelled{background:var(--myhome-error-pastel);color:var(--myhome-error-ink)}.outcome-icon.cancelled:before{content:"\2715"}.outcome-icon.expired{background:var(--myhome-warning-pastel);color:var(--myhome-warning-ink)}.outcome-icon.expired:before{content:"\29d7"}.outcome-icon.problem{background:var(--myhome-error-pastel);color:var(--myhome-error-ink)}.outcome-icon.problem:before{content:"!"}.drawing{height:230px;border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);margin:0 0 16px;background-color:var(--myhome-drawing-paper);background-repeat:no-repeat}.prose p{margin:0 0 12px;font-size:14.5px;line-height:1.6;text-wrap:pretty}.prose ul{margin:0 0 12px;padding-left:20px;font-size:14.5px;line-height:1.6}.prose .md-image{display:block;max-width:100%;border-radius:var(--myhome-radius);margin:0 0 12px}.big{width:100%;min-height:64px;border:none;border-radius:16px;font:inherit;font-size:16px;font-weight:600;cursor:pointer;background:var(--myhome-primary);color:var(--myhome-text-on-primary);box-shadow:var(--myhome-shadow)}.big.moving{background:var(--myhome-accent);color:var(--myhome-text)}.big[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default;box-shadow:none}.options{display:flex;flex-direction:column;gap:8px;margin:4px 0 0}.option{text-align:left;border-radius:10px;font:inherit;padding:14px;min-height:56px;cursor:pointer;color:inherit;border:1px solid var(--myhome-field-border);background:var(--myhome-card)}.option[aria-pressed=true]{border-color:var(--myhome-primary-ink);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.option .option-head{display:flex;align-items:center;gap:8px}.option .option-title{font-weight:500;flex:1;font-size:14.5px;line-height:1.4}.option .option-meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:3px}.live{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:14px 16px;display:flex;flex-direction:column;gap:8px;font-size:14px}.live-row{display:flex;justify-content:space-between;gap:12px}.live-row .name{color:var(--myhome-text-soft)}.live-row .value{font-variant-numeric:tabular-nums;font-weight:500}.live-row .value.moving{color:var(--myhome-warning-ink);animation:myhome-pulse 1.2s ease-in-out infinite}@keyframes myhome-pulse{0%,to{opacity:1}50%{opacity:.55}}.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.instruction{margin:0 0 16px;font-size:16.5px;line-height:1.5;font-weight:500}.note{margin:14px 0 0;border-radius:8px;padding:12px 14px;font-size:14px;line-height:1.55}.note.success{background:var(--myhome-success-pastel)}.note.error{background:var(--myhome-error-pastel)}.note.info{background:var(--myhome-info-pastel)}.progress-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px}.progress-track{height:8px;border-radius:4px;background:var(--myhome-background-soft);overflow:hidden}.progress-bar{height:100%;background:var(--myhome-primary);border-radius:4px;transition:width .1s linear}.progress-eta{margin:10px 0 0;font-size:13px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}.reading{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:4px 0 0}.reading label{display:block;font-size:13.5px;margin:0 0 8px}.reading .row{display:flex;align-items:center;gap:10px}.reading input{flex:1;min-width:0;height:56px;border-radius:10px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:inherit;padding:0 14px;font:inherit;font-size:26px;font-variant-numeric:tabular-nums}.reading.big input{height:64px;font-size:32px}.reading .unit{font-size:16px;color:var(--myhome-text-soft)}.reading.big .unit{font-size:18px}.reading .hint{margin:8px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.reading .error{margin:8px 0 0;font-size:12.5px;color:var(--myhome-error-ink);line-height:1.5}.summary{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:8px 16px;margin:4px 0 14px}.summary-row{display:flex;align-items:baseline;gap:8px;padding:9px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.summary-row:last-of-type{border-bottom:none}.summary-row .label{flex:1 1 130px;color:var(--myhome-text-soft)}.summary-row .before{color:var(--myhome-text-soft);font-variant-numeric:tabular-nums;text-decoration:line-through;opacity:.7}.summary-row .after{font-variant-numeric:tabular-nums;font-weight:500}.summary .note-line{margin:10px 0;font-size:12.5px;color:var(--myhome-text-soft)}.code{background:var(--myhome-background-soft);border-radius:8px;padding:12px 14px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-x:auto}.stub{margin:4px 0 0;background:var(--myhome-info-pastel);border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.55}`;var He=class extends f{constructor(){super();this._fire=(e,t)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:e,value:t,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new y}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[E,P,S,D,xe,Ci,u`:host{display:block;background:transparent}.screen{width:100%;max-width:480px;margin:0 auto;display:flex;flex-direction:column;position:relative}.pane{flex:1;padding:16px 16px 230px}.right{min-width:0}.footer{position:fixed;bottom:0;left:50%;transform:translate(-50%);width:100%;max-width:480px;padding:36px 16px calc(12px + env(safe-area-inset-bottom,0px));background:linear-gradient(to top,var(--myhome-background) calc(100% - 36px),transparent);z-index:25;display:flex;flex-direction:column;gap:10px}@media(min-width:900px){.screen{max-width:100%}.pane{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:0 44px;align-items:start;width:100%;max-width:1080px;margin:0 auto;padding:24px 32px 48px}.pane.single{display:block;max-width:560px}.right{position:sticky;top:76px}.footer{position:static;transform:none;width:auto;max-width:none;padding:0;background:none;margin-top:20px}}`]}_renderOperative(e,t){switch(e.model){case"scelta":return $i(e,t);case"pos":return ki(e,t);case"click":return Ri(e,t);case"controllo":return Ei(e,t);case"metro":return Pi(e,t);case"riepilogo":return Si(e,t);case"esito":return Ti(e,t);case"lettura":return xi(e,t);default:return l}}_renderFooter(e,t){let r=e.secondary??[];return!e.primary&&r.length===0?l:s`<div class="footer">
      ${e.primary?s`<button
            class="big ${e.press?.state==="moving"?"moving":""}"
            type="button"
            ?disabled=${e.primary.disabled}
            @click=${()=>this._fire(e.primary.action)}
          >
            ${e.primary.label}
          </button>`:l}
      ${r.map(o=>s`<button
          class="cta ${o.kind==="text"?"text":"secondary"}"
          type="button"
          ?disabled=${o.disabled}
          @click=${()=>t.fire(o.action)}
        >
          ${o.label}
        </button>`)}
    </div>`}render(){let e=this.model;if(!e)return l;let t={i18n:this.i18n,fire:this._fire},r=e.model==="pos",o=e.image?Tt(e.image):null;return s`<div class="screen">
      <div class="pane ${r?"single":""}">
        <div class="text-column">
          ${e.phase?s`<p class="phase">
                ${this.i18n.t("panel.screen.phase",{phase:e.phase.label,index:e.phase.index,count:e.phase.count})}
              </p>`:l}
          ${e.newText?s`<p class="new-text">${this.i18n.t("panel.screen.new_text")}</p>`:l}
          <h1 class="screen-title">
            ${e.outcome?s`<span class="outcome-icon ${e.outcome}" aria-hidden="true"></span>`:l}
            <span>${e.title}</span>
          </h1>
          ${o?s`<div
                class="drawing"
                role="img"
                aria-label=${e.image?.alt??""}
                style=${Re(o)}
              ></div>`:l}
          ${e.body?s`<div class="prose">${K(e.body)}</div>`:l}
        </div>
        <div class="right">
          ${this._renderOperative(e,t)} ${this._renderFooter(e,t)}
        </div>
      </div>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",He);var dn=3e4,cn=7e3,at=400,hn=2e3,lt=class extends f{constructor(){super();this._i18n=new y;this._router=new we;this._store=new be(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._snackTimer=null;this._previewTimer=null;this._travelTimer=null;this._impactTimer=null;this._followTimer=null;this._followedAt=0;this._listening=Promise.resolve();this._subscribing=0;this._previewSeq=0;this._onSocketDown=()=>{this._store.state.connection!=="offline"&&(this._store.set({connection:"offline"}),this._store.announce(this._i18n.t("panel.error.no_connection")))};this._onSocketReady=()=>{this._afterReconnect()};this._onReturn=()=>{!this._started||document.hidden||this._refresh()};this._assignActions={search:e=>this._store.set({search:e}),room:e=>this._store.set({room:e}),clearFilters:()=>this._store.set({search:"",room:""}),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:(e,t)=>{if(this._locked)return;let{pending:r,withdrawn:o}=Kt(this._store.state.pending,e,t);this._store.set({pending:r,dialog:null,armed:null,writeError:null}),this._store.announce(o?this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name}):this._i18n.t("panel.assign.announce.pending",{cover:e.name,target:t===null?this._i18n.t("panel.assign.target_none"):this._i18n.t("panel.assign.target_profile",{profile:t})})),this._schedulePreview()},withdraw:e=>{this._store.set({pending:this._store.state.pending.filter(t=>t.cover!==e.unique_id)}),this._store.announce(this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name})),this._schedulePreview()},discardAll:()=>{this._store.set({...ye}),this._store.announce(this._i18n.t("panel.assign.announce.discarded"))},reorder:e=>{this._locked||!this._store.state.entryId||(this._store.set({order:e}),this._write(()=>Ot(this.hass.connection,this._store.state.entryId,e),t=>{this._store.set({order:null}),this._store.setOverview(t.overview),this._snack(this._i18n.t("panel.toast.order_saved"),t.undo_token),this._store.announce(this._i18n.t("panel.assign.announce.reordered"))},t=>{this._store.set({order:null,writeError:null}),this._snack(t,null,!1)}))},setOrder:e=>this._store.set({order:e}),drag:e=>this._store.set({drag:e?{cover:e.unique_id,name:e.name,over:null,insert:null}:null}),over:e=>{let t=this._store.state.drag;t&&this._store.set({drag:{...t,over:e?.group??null,insert:e?{...e}:null}})},arm:e=>{this._store.set({armed:e?e.unique_id:null}),e&&this._store.announce(this._i18n.t("panel.assign.announce.armed"))},dialog:e=>this._store.set({dialog:e?e.unique_id:null}),review:e=>{this._store.set({review:e,writeError:null,heightsForced:!1}),e&&this._refreshPreview()},height:(e,t)=>{this._store.set({heights:{...this._store.state.heights,[e]:t}}),this._schedulePreview()},toggleShowAll:()=>this._store.set({showAll:!this._store.state.showAll}),confirm:()=>{this._confirm()},undo:()=>{this._undo()},announce:e=>this._store.announce(e)};this._detailActions={back:()=>this._navigate("/"),retry:()=>{this._store.set({detail:{...this._store.state.detail,loading:!0,error:null}}),this._loadDetail()},openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:()=>{let e=this._store.state.detail.for;this._store.set({dialog:e}),this._navigate("/")},mode:e=>{let t=this._store.state.detail,r=this._detailCover,o=e==="edit"?this._detailForm():e==="travel"?{height:r?.height!=null?this._i18n.number(r.height,0):""}:{};this._store.set({detail:{...t,mode:e,form:o,errors:{},preview:null,previewing:!1},writeError:null}),e==="travel"&&this._refreshTravelPreview()},field:(e,t)=>{let r=this._store.state.detail,o=e==="height"&&b("height",t)!==null;o&&(this._previewSeq+=1),this._store.set({detail:{...r,form:{...r.form,[e]:t},...o?{preview:null}:{}}}),e==="height"&&this._scheduleTravelPreview()},saveValues:()=>{this._saveValues()},saveTravel:()=>{this._saveTravel()},remove:()=>{this._removeMeasure()},openFlow:e=>this._openFlow(e)};this._profileActions={back:()=>this._navigate("/"),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),mode:e=>{let t=this._store.state.profile;this._store.set({profile:{...t,mode:e,form:e==="edit"?this._profileForm(this._profileRow):{},errors:{},newName:e==="rename"?t.for??"":"",nameError:"",impact:null,impacting:!1},writeError:null}),e==="edit"&&this._refreshImpact()},field:(e,t)=>{let r=this._store.state.profile;this._store.set({profile:{...r,form:{...r.form,[e]:t}}}),this._scheduleImpact()},newName:e=>this._store.set({profile:{...this._store.state.profile,newName:e,nameError:""}}),saveValues:()=>{this._saveProfile()},rename:()=>{this._renameProfile()},remove:()=>{this._deleteProfile()}};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[E,P,S,xe,ei,Ee,Se,u`.toolbar{display:flex;align-items:center;gap:8px;padding:0 8px;background:var(--myhome-header);color:var(--myhome-header-text);font-size:20px;font-weight:400;padding-top:env(safe-area-inset-top,0px);height:calc(56px + env(safe-area-inset-top,0px))}.toolbar .title{flex:1;min-width:0;margin:0;font-size:inherit;font-weight:inherit;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar select.gateway{font:inherit;font-size:13px;max-width:40%;min-height:44px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;padding:0 6px}.toolbar select.gateway option{color:var(--myhome-text);background:var(--myhome-card)}.toolbar button{width:48px;height:48px;flex:0 0 48px;border:0;border-radius:24px;background:transparent;color:inherit;font-size:20px;line-height:1;cursor:pointer}.content{padding:16px;max-width:1200px;margin:0 auto;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}.card.problem{background:var(--myhome-error-pastel);color:var(--myhome-text);padding:16px}.card.waiting{color:var(--myhome-text-soft);padding:16px}.soft{color:var(--myhome-text-soft);font-size:13px;margin-top:8px}.connection{margin:24px 0 0;font-size:12.5px;color:var(--myhome-text-soft)}.offline{display:block;padding:12px 16px;background:var(--myhome-warning-pastel);color:var(--myhome-text);font-size:14px}a{color:var(--myhome-primary-ink)}`]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(e=>this._onRoute(e)),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._unwatchSocket(),this._stopPolling(),this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._previewTimer&&(clearTimeout(this._previewTimer),this._previewTimer=null),this._travelTimer&&(clearTimeout(this._travelTimer),this._travelTimer=null),this._impactTimer&&(clearTimeout(this._impactTimer),this._impactTimer=null),this._followTimer&&(clearTimeout(this._followTimer),this._followTimer=null);let e=this._unsubscribeWs;this._unsubscribeWs=null,e?.().catch(()=>{})}shouldUpdate(e){return e.size>1||!e.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(e){if(e.has("route")&&(this._router.setHostPath(this.route?.path),this._onRoute(this._router.current)),!(!e.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_languageOf(e){return e?.locale?.language||e?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,this._watchSocket(),await this._loadTexts(),await this._refresh(),await this._loadDetail(),await this._listen())}_watchSocket(){let e=this.hass?.connection;e?.addEventListener?.("disconnected",this._onSocketDown),e?.addEventListener?.("ready",this._onSocketReady)}_unwatchSocket(){let e=this.hass?.connection;e?.removeEventListener?.("disconnected",this._onSocketDown),e?.removeEventListener?.("ready",this._onSocketReady)}async _afterReconnect(){this._started&&(this._store.set({connection:this._unsubscribeWs?"live":"polling"}),await this._refresh(),!this._unsubscribeWs&&!this._subscribing&&await this._listen(),this._store.announce(this._i18n.t("panel.common.reconnected")))}async _loadTexts(){let e=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,e)}catch{}this._language=e,this.requestUpdate()}async _refresh(){try{let e=await Ct(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(e)}catch(e){this._store.setError(I(e))}}_listen(){this._subscribing+=1;let e=this._listening.then(()=>this._subscribeOnce()).finally(()=>{this._subscribing-=1});return this._listening=e.catch(()=>{}),e}async _subscribeOnce(){let e=this._unsubscribeWs;this._unsubscribeWs=null,await e?.().catch(()=>{});try{let t=await Mt(this.hass.connection,this._store.state.entryId,r=>this._onEvent(r));if(!this.isConnected){t().catch(()=>{});return}this._unsubscribeWs=t,this._store.set({connection:"live"}),this._stopPolling()}catch(t){te(t)||console.warn("MyHOME panel: live updates are not available",I(t)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(e){if(e.type==="overview"){this._store.setOverview(e.overview),this._followPush();return}if(e.type==="measuring"){let t=this._store.state.overview;if(!t)return;this._store.set({overview:{...t,measuring:e.cover_unique_id?{cover_unique_id:e.cover_unique_id,name:e.name??""}:null}}),e.cover_unique_id&&(this._store.set({armed:null,drag:null}),this._store.announce(this._i18n.t("panel.banner.measuring.body",{cover:e.name??""})))}}_followPush(){if(this._followTimer)return;let e=Math.max(0,hn-(Date.now()-this._followedAt));this._followTimer=setTimeout(()=>{this._followTimer=null,this._followedAt=Date.now(),this._store.state.review&&this._schedulePreview(),this._store.state.detail.for&&this._loadDetail()},e)}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},dn))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}_onRoute(e){if(this._store.set({route:e}),e.view==="cover"){let t=e.params.id;this._store.state.detail.for!==t&&(this._store.set({detail:{...re,for:t,loading:!0}}),this._loadDetail())}else this._store.state.detail.for!==null&&this._store.set({detail:re});if(e.view==="profile"){let t=e.params.name;this._store.state.profile.for!==t&&this._store.set({profile:{...oe,for:t}})}else this._store.state.profile.for!==null&&this._store.set({profile:oe});this._started&&this._store.set({writeError:null})}get _version(){return this.panel?.config?.version??""}_navigate(e){this._router.navigate(e)}_renderMenuButton(){return this.narrow?Wt("ha-menu-button")?s`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:s`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>Bt(this)}
    >
      ☰
    </button>`:l}_renderBackButton(){return this._store.state.route.view==="overview"?l:s`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.back")}
      @click=${()=>this._navigate("/")}
    >
      ←
    </button>`}_renderPlaceholder(e,t){let r={id:"panel.common.not_yet",model:"lettura",title:e,body:t,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return s`<myhome-screen
      .model=${r}
      .i18n=${this._i18n}
      @myhome-screen-action=${o=>{o.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}get _locked(){let e=this._store.state;return e.overview?.measuring!=null||e.applying}async _confirm(){let e=this._store.state,t=e.entryId;if(this._locked||!t||e.pending.length===0)return;if(e.pending.filter(p=>{let d=e.overview?.covers.find(c=>c.unique_id===p.cover);return d!==void 0&&Vt(d,p)&&ie(e.heights[p.cover])!==null}).length>0){this._store.set({heightsForced:!0}),this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));return}let o=it(e.pending,e.heights),a=e.order??void 0;this._store.announce(this._i18n.t("panel.assign.announce.applying")),await this._write(()=>Lt(this.hass.connection,t,o,a),p=>{this._store.set({...ye}),this._store.setOverview(p.overview),this._snack(p.applied===1?this._i18n.t("panel.toast.assigned_one"):this._i18n.t("panel.toast.assigned",{count:p.applied}),p.undo_token)})}async _undo(){let e=this._store.state,t=e.snack?.undoToken;if(!t||!e.entryId)return;let r=e.entryId;this._clearSnack(),await this._write(()=>Ut(this.hass.connection,r,t),o=>{this._store.setOverview(o.overview),this._snack(this._i18n.t("panel.toast.undone"),null)})}async _write(e,t,r){this._store.set({applying:!0,writeError:null});try{let o=await e();this._store.set({applying:!1}),t(o)}catch(o){let a=I(o);this._store.set({applying:!1,writeError:a});let p=this._i18n.refusal(a.translation_key,a.translation_placeholders??{});this._store.announce(p),r?.(p)}}_snack(e,t,r=!0){this._clearSnack(),this._store.set({snack:{message:e,undoToken:t}}),r&&this._store.announce(e),this._snackTimer=setTimeout(()=>{this._snackTimer=null,this._store.set({snack:null})},cn)}_clearSnack(){this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._store.set({snack:null})}_schedulePreview(){this._store.state.review&&(this._previewTimer&&clearTimeout(this._previewTimer),this._previewTimer=setTimeout(()=>{this._previewTimer=null,this._refreshPreview()},at))}async _refreshPreview(){let e=this._store.state;if(!e.entryId||e.pending.length===0){this._store.set({preview:null});return}let t=++this._previewSeq;this._store.set({previewing:!0});try{let r=await me(this.hass.connection,e.entryId,it(e.pending,e.heights));t===this._previewSeq&&this._store.set({preview:r.items,previewing:!1})}catch(r){t===this._previewSeq&&this._store.set({previewing:!1}),te(r)||console.warn("MyHOME panel: the preview could not be read",I(r))}}get _detailCover(){let e=this._store.state,t=e.detail.for;return e.overview?.covers.find(r=>r.unique_id===t)??null}async _loadDetail(){let e=this._store.state,t=e.detail.for;if(!(!this._started||!this.hass||!t||!e.entryId))try{let r=await It(this.hass.connection,e.entryId,t);if(this._store.state.detail.for!==t)return;this._store.set({detail:{...this._store.state.detail,answer:r,loading:!1,error:null}})}catch(r){if(this._store.state.detail.for!==t)return;this._store.set({detail:{...this._store.state.detail,answer:null,loading:!1,error:I(r)}})}}_detailForm(){let e=this._store.state.detail.answer,t={};for(let r of j){let o=e?.keys.find(a=>a.key===r);t[r]=o&&o.own?this._i18n.number(o.value,$[r]??1):""}return t}async _saveValues(){let e=this._store.state,t=e.detail.for;if(this._locked||!t||!e.entryId)return;let r={};for(let d of j){let c=e.detail.form[d];if(b(d,c)!==null)return;r[d]=k(c)?null:M(c??"")}let o=Object.values(r).every(d=>d===null),a=this._detailCover?.name??"",p=e.entryId;await this._write(()=>Dt(this.hass.connection,p,t,r),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{}}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(o?this._i18n.t("panel.toast.measure_removed",{cover:a,destination:this._destinationOf(d.overview,t)}):this._i18n.t("panel.toast.values_saved",{cover:a}),d.undo_token)})}async _saveTravel(){let e=this._store.state,t=e.detail.for,r=e.detail.form.height;if(this._locked||!t||!e.entryId||k(r)||b("height",r))return;let o=M(r??""),a=this._detailCover?.name??"",p=e.entryId;await this._write(()=>zt(this.hass.connection,p,t,o),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{},preview:null}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.travel_saved",{cover:a}),d.undo_token)})}async _removeMeasure(){let e=this._store.state,t=e.detail.for;if(this._locked||!t||!e.entryId)return;let r=this._detailCover?.name??"",o=e.entryId;await this._write(()=>Ht(this.hass.connection,o,t),a=>{this._store.set({detail:{...this._store.state.detail,mode:"view"}}),this._store.setOverview(a.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.measure_removed",{cover:r,destination:a.falls_back_to==="profile"?this._i18n.t("panel.detail.destination.profile",{profile:a.profile??""}):a.falls_back_to==="file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}),a.undo_token)})}_destinationOf(e,t){let r=e.covers.find(o=>o.unique_id===t);return r?.origin==="inherited"||r?.origin==="adjusted"?this._i18n.t("panel.detail.destination.profile",{profile:r.profile??""}):r?.origin==="from_the_file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}_scheduleTravelPreview(){this._travelTimer&&clearTimeout(this._travelTimer),this._travelTimer=setTimeout(()=>{this._travelTimer=null,this._refreshTravelPreview()},at)}async _refreshTravelPreview(){let e=this._store.state,t=this._detailCover,r=e.detail.form.height;if(!e.entryId||!t||k(r)||b("height",r)!==null){this._store.set({detail:{...this._store.state.detail,preview:null}});return}let o=++this._previewSeq;this._store.set({detail:{...this._store.state.detail,previewing:!0}});try{let a=await me(this.hass.connection,e.entryId,[{...nt(t),height:M(r??"")}]);if(o!==this._previewSeq)return;this._store.set({detail:{...this._store.state.detail,preview:a.items[0]??null,previewing:!1}})}catch(a){o===this._previewSeq&&this._store.set({detail:{...this._store.state.detail,previewing:!1}}),te(a)||console.warn("MyHOME panel: the preview could not be read",I(a))}}_openFlow(e){Xt({source:e,entryId:this._store.state.entryId,onLeaving:()=>this._store.announce(this._i18n.t("panel.common.opens_configure"))})}_title(){let e=this._store.state,t=e.route;if(t.view==="cover"){let r=this._detailCover;return r?this._i18n.t("panel.detail.named",{cover:r.name}):this._i18n.t("panel.detail.title")}return t.view==="profile"?e.overview?.profiles.some(o=>o.name===t.params.name)?this._i18n.t("panel.profile.name",{profile:t.params.name}):this._i18n.t("panel.profile.title"):this._i18n.t("panel.overview.title")}get _profileRow(){let e=this._store.state;return e.overview?.profiles.find(t=>t.name===e.profile.for)??null}_followersOf(e){let t=this._store.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return t.filter(o=>r.has(o.unique_id))}_profileForm(e){let t={};for(let r of G){let o=r==="reference_height"?e?.reference_height:e?.values[r];t[r]=o==null?"":this._i18n.number(o,$[r]??0)}return t}_typedProfile(){let e=this._store.state.profile.form,t={};for(let r of G){if(k(e[r])||b(r,e[r])!==null)return null;t[r]=M(e[r]??"")}return t}async _saveProfile(){let e=this._store.state,t=e.profile.for,r=this._typedProfile();if(this._locked||!t||!e.entryId||!r)return;let{reference_height:o,...a}=r,p=e.entryId;await this._write(()=>Nt(this.hass.connection,p,t,a,o),d=>{this._store.set({profile:{...this._store.state.profile,mode:"view",impact:null}}),this._store.setOverview(d.overview),this._snack(d.affected.length===1?this._i18n.t("panel.toast.profile_saved_one",{profile:t}):this._i18n.t("panel.toast.profile_saved",{profile:t,count:d.affected.length}),d.undo_token)})}async _renameProfile(){let e=this._store.state,t=e.profile.for,r=e.profile.newName.trim();if(this._locked||!t||!e.entryId||!r||r===t)return;let o=e.entryId;await this._write(()=>qt(this.hass.connection,o,t,r),a=>{this._store.setOverview(a.overview),this._navigate(`/profile/${encodeURIComponent(r)}`),this._snack(this._i18n.t("panel.toast.profile_renamed",{profile:r}),a.undo_token)},a=>this._store.set({profile:{...this._store.state.profile,nameError:a},writeError:null}))}async _deleteProfile(){let e=this._store.state,t=e.profile.for;if(this._locked||!t||!e.entryId)return;let r=e.entryId;await this._write(()=>Ft(this.hass.connection,r,t),o=>{this._store.setOverview(o.overview),this._navigate("/"),this._snack(this._i18n.t("panel.toast.profile_deleted",{profile:t}),o.undo_token)})}_scheduleImpact(){this._impactTimer&&clearTimeout(this._impactTimer),this._impactTimer=setTimeout(()=>{this._impactTimer=null,this._refreshImpact()},at)}async _refreshImpact(){let e=this._store.state,t=this._typedProfile(),r=e.profile.for,o=this._followersOf(this._profileRow);if(!e.entryId||!r||!t||o.length===0){this._store.set({profile:{...this._store.state.profile,impact:null}});return}let a=++this._previewSeq;this._store.set({profile:{...this._store.state.profile,impacting:!0}});try{let p=await me(this.hass.connection,e.entryId,o.map(d=>nt(d)),{[r]:t});if(a!==this._previewSeq)return;this._store.set({profile:{...this._store.state.profile,impact:p.items,impacting:!1}})}catch(p){a===this._previewSeq&&this._store.set({profile:{...this._store.state.profile,impacting:!1}}),te(p)||console.warn("MyHOME panel: the impact preview could not be read",I(p))}}async _retry(){await this._refresh(),this._store.state.connection!=="live"&&await this._listen()}_renderView(){let e=this._store.state;if(e.status==="loading")return e.route.view==="cover"||e.route.view==="profile"?Pe(this._i18n):si(this._i18n);if(e.status==="error"||!e.overview){let r=e.error;return s`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(r?.translation_key,r?.translation_placeholders??{})}
        </div>
        <div class="soft">${r?`${r.code}: ${r.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._retry()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${R}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?s` · ${this._version}`:l}
        </div>
      </div>`}let t=e.route;return t.view==="cover"?s`<myhome-cover-detail
        .i18n=${this._i18n}
        .state=${e}
        .actions=${this._detailActions}
      ></myhome-cover-detail>`:t.view==="profile"?s`<myhome-profile-card
        .i18n=${this._i18n}
        .state=${e}
        .actions=${this._profileActions}
      ></myhome-profile-card>`:t.view!=="overview"?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):s`<myhome-overview
      .i18n=${this._i18n}
      .state=${e}
      .actions=${this._assignActions}
    ></myhome-overview>`}render(){let e=this._store.state,t=this._title(),r=e.overview?.measuring??null,o=e.route.view!=="overview";return s`
      <!--
        One named landmark for everything the panel draws, and deliberately not "main" or
        "banner": a custom panel is rendered inside Home Assistant's own document and the
        shell owns those. A region named by the page's own heading is a landmark a reader
        can jump to and one that cannot collide with the host's.
      -->
      <div class="page" role="region" aria-labelledby="panel-title">
        <div class="toolbar">
          ${this._renderMenuButton()} ${this._renderBackButton()}
          <h1 class="title" id="panel-title">${t}</h1>
          ${this._renderGatewayPicker()}
        </div>
      ${e.connection==="offline"?s`<div class="offline" role="status">
            ${this._i18n.t("panel.error.no_connection")}
          </div>`:l}
      ${r?ti(this._i18n,r.name,R):l}
      <div class="content">
        ${Jt(e.announce)} ${this._renderView()}
        ${e.connection==="polling"&&e.status==="ready"?s`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:l}
      </div>
      <!--
        The overview draws its own five strips, because three of them are about a gesture
        it owns. The routed cards have no gestures and two of the five still apply to them:
        a write in the air, and what it came to with "Annulla" beside it.
      -->
      ${o&&e.applying?Te(this._i18n):l}
      ${o&&e.snack&&!e.applying?Ce(this._i18n,e.snack.message,e.snack.undoToken?()=>{this._undo()}:null):l}
      </div>
    `}_renderGatewayPicker(){let e=this._store.state,t=e.overview?.entries??[],r=t.find(a=>a.entry_id===e.entryId);if(t.length<=1)return l;let o=this._i18n.t("panel.common.gateway",{gateway:r?.title??""});return s`<select
      class="gateway"
      aria-label=${o}
      .value=${e.entryId??""}
      ?disabled=${e.applying}
      @change=${a=>{this._switchGateway(a.target.value)}}
    >
      ${t.map(a=>s`<option value=${a.entry_id} ?selected=${a.entry_id===e.entryId}>
          ${a.title}
        </option>`)}
    </select>`}async _switchGateway(e){if(!e||e===this._store.state.entryId)return;let t=this._unsubscribeWs;this._unsubscribeWs=null,await t?.().catch(()=>{}),this._clearSnack(),this._store.set({...ye,entryId:e,detail:re,profile:oe,search:"",room:"",snack:null}),this._navigate("/"),await this._refresh(),await this._listen()}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",lt);export{lt as MyHomeCalibrationPanel};
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
