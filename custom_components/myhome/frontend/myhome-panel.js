/* MyHOME calibration panel */
var le=globalThis,pe=le.ShadowRoot&&(le.ShadyCSS===void 0||le.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Oe=Symbol(),nt=new WeakMap,G=class{constructor(i,e,t){if(this._$cssResult$=!0,t!==Oe)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=i,this.t=e}get styleSheet(){let i=this.o,e=this.t;if(pe&&i===void 0){let t=e!==void 0&&e.length===1;t&&(i=nt.get(e)),i===void 0&&((this.o=i=new CSSStyleSheet).replaceSync(this.cssText),t&&nt.set(e,i))}return i}toString(){return this.cssText}},rt=n=>new G(typeof n=="string"?n:n+"",void 0,Oe),u=(n,...i)=>{let e=n.length===1?n[0]:i.reduce((t,r,o)=>t+(s=>{if(s._$cssResult$===!0)return s.cssText;if(typeof s=="number")return s;throw Error("Value passed to 'css' function must be a 'css' function result: "+s+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+n[o+1],n[0]);return new G(e,n,Oe)},ot=(n,i)=>{if(pe)n.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of i){let t=document.createElement("style"),r=le.litNonce;r!==void 0&&t.setAttribute("nonce",r),t.textContent=e.cssText,n.appendChild(t)}},ze=pe?n=>n:n=>n instanceof CSSStyleSheet?(i=>{let e="";for(let t of i.cssRules)e+=t.cssText;return rt(e)})(n):n;var{is:$i,defineProperty:ki,getOwnPropertyDescriptor:Ri,getOwnPropertyNames:Ei,getOwnPropertySymbols:Pi,getPrototypeOf:Ti}=Object,de=globalThis,st=de.trustedTypes,Si=st?st.emptyScript:"",Ci=de.reactiveElementPolyfillSupport,V=(n,i)=>n,De={toAttribute(n,i){switch(i){case Boolean:n=n?Si:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,i){let e=n;switch(i){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},lt=(n,i)=>!$i(n,i),at={attribute:!0,type:String,converter:De,reflect:!1,useDefault:!1,hasChanged:lt};Symbol.metadata??=Symbol("metadata"),de.litPropertyMetadata??=new WeakMap;var T=class extends HTMLElement{static addInitializer(i){this._$Ei(),(this.l??=[]).push(i)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(i,e=at){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(i)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(i,e),!e.noAccessor){let t=Symbol(),r=this.getPropertyDescriptor(i,t,e);r!==void 0&&ki(this.prototype,i,r)}}static getPropertyDescriptor(i,e,t){let{get:r,set:o}=Ri(this.prototype,i)??{get(){return this[e]},set(s){this[e]=s}};return{get:r,set(s){let p=r?.call(this);o?.call(this,s),this.requestUpdate(i,p,t)},configurable:!0,enumerable:!0}}static getPropertyOptions(i){return this.elementProperties.get(i)??at}static _$Ei(){if(this.hasOwnProperty(V("elementProperties")))return;let i=Ti(this);i.finalize(),i.l!==void 0&&(this.l=[...i.l]),this.elementProperties=new Map(i.elementProperties)}static finalize(){if(this.hasOwnProperty(V("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(V("properties"))){let e=this.properties,t=[...Ei(e),...Pi(e)];for(let r of t)this.createProperty(r,e[r])}let i=this[Symbol.metadata];if(i!==null){let e=litPropertyMetadata.get(i);if(e!==void 0)for(let[t,r]of e)this.elementProperties.set(t,r)}this._$Eh=new Map;for(let[e,t]of this.elementProperties){let r=this._$Eu(e,t);r!==void 0&&this._$Eh.set(r,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(i){let e=[];if(Array.isArray(i)){let t=new Set(i.flat(1/0).reverse());for(let r of t)e.unshift(ze(r))}else i!==void 0&&e.push(ze(i));return e}static _$Eu(i,e){let t=e.attribute;return t===!1?void 0:typeof t=="string"?t:typeof i=="string"?i.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(i=>this.enableUpdating=i),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(i=>i(this))}addController(i){(this._$EO??=new Set).add(i),this.renderRoot!==void 0&&this.isConnected&&i.hostConnected?.()}removeController(i){this._$EO?.delete(i)}_$E_(){let i=new Map,e=this.constructor.elementProperties;for(let t of e.keys())this.hasOwnProperty(t)&&(i.set(t,this[t]),delete this[t]);i.size>0&&(this._$Ep=i)}createRenderRoot(){let i=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ot(i,this.constructor.elementStyles),i}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(i=>i.hostConnected?.())}enableUpdating(i){}disconnectedCallback(){this._$EO?.forEach(i=>i.hostDisconnected?.())}attributeChangedCallback(i,e,t){this._$AK(i,t)}_$ET(i,e){let t=this.constructor.elementProperties.get(i),r=this.constructor._$Eu(i,t);if(r!==void 0&&t.reflect===!0){let o=(t.converter?.toAttribute!==void 0?t.converter:De).toAttribute(e,t.type);this._$Em=i,o==null?this.removeAttribute(r):this.setAttribute(r,o),this._$Em=null}}_$AK(i,e){let t=this.constructor,r=t._$Eh.get(i);if(r!==void 0&&this._$Em!==r){let o=t.getPropertyOptions(r),s=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:De;this._$Em=r;let p=s.fromAttribute(e,o.type);this[r]=p??this._$Ej?.get(r)??p,this._$Em=null}}requestUpdate(i,e,t,r=!1,o){if(i!==void 0){let s=this.constructor;if(r===!1&&(o=this[i]),t??=s.getPropertyOptions(i),!((t.hasChanged??lt)(o,e)||t.useDefault&&t.reflect&&o===this._$Ej?.get(i)&&!this.hasAttribute(s._$Eu(i,t))))return;this.C(i,e,t)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(i,e,{useDefault:t,reflect:r,wrapped:o},s){t&&!(this._$Ej??=new Map).has(i)&&(this._$Ej.set(i,s??e??this[i]),o!==!0||s!==void 0)||(this._$AL.has(i)||(this.hasUpdated||t||(e=void 0),this._$AL.set(i,e)),r===!0&&this._$Em!==i&&(this._$Eq??=new Set).add(i))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let i=this.scheduleUpdate();return i!=null&&await i,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[r,o]of this._$Ep)this[r]=o;this._$Ep=void 0}let t=this.constructor.elementProperties;if(t.size>0)for(let[r,o]of t){let{wrapped:s}=o,p=this[r];s!==!0||this._$AL.has(r)||p===void 0||this.C(r,void 0,o,p)}}let i=!1,e=this._$AL;try{i=this.shouldUpdate(e),i?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(t){throw i=!1,this._$EM(),t}i&&this._$AE(e)}willUpdate(i){}_$AE(i){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(i)),this.updated(i)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(i){return!0}update(i){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(i){}firstUpdated(i){}};T.elementStyles=[],T.shadowRootOptions={mode:"open"},T[V("elementProperties")]=new Map,T[V("finalized")]=new Map,Ci?.({ReactiveElement:T}),(de.reactiveElementVersions??=[]).push("2.1.2");var Be=globalThis,pt=n=>n,ce=Be.trustedTypes,dt=ce?ce.createPolicy("lit-html",{createHTML:n=>n}):void 0,gt="$lit$",O=`lit$${Math.random().toFixed(9).slice(2)}$`,ft="?"+O,Ai=`<${ft}>`,q=document,X=()=>q.createComment(""),Z=n=>n===null||typeof n!="object"&&typeof n!="function",Ke=Array.isArray,Ii=n=>Ke(n)||typeof n?.[Symbol.iterator]=="function",He=`[ 	
\f\r]`,Y=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ct=/-->/g,ht=/>/g,H=RegExp(`>|${He}(?:([^\\s"'>=/]+)(${He}*=${He}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ut=/'/g,mt=/"/g,_t=/^(?:script|style|textarea|title)$/i,je=n=>(i,...e)=>({_$litType$:n,strings:i,values:e}),a=je(1),dn=je(2),cn=je(3),S=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),vt=new WeakMap,N=q.createTreeWalker(q,129);function wt(n,i){if(!Ke(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return dt!==void 0?dt.createHTML(i):i}var Mi=(n,i)=>{let e=n.length-1,t=[],r,o=i===2?"<svg>":i===3?"<math>":"",s=Y;for(let p=0;p<e;p++){let d=n[p],c,m,h=-1,v=0;for(;v<d.length&&(s.lastIndex=v,m=s.exec(d),m!==null);)v=s.lastIndex,s===Y?m[1]==="!--"?s=ct:m[1]!==void 0?s=ht:m[2]!==void 0?(_t.test(m[2])&&(r=RegExp("</"+m[2],"g")),s=H):m[3]!==void 0&&(s=H):s===H?m[0]===">"?(s=r??Y,h=-1):m[1]===void 0?h=-2:(h=s.lastIndex-m[2].length,c=m[1],s=m[3]===void 0?H:m[3]==='"'?mt:ut):s===mt||s===ut?s=H:s===ct||s===ht?s=Y:(s=H,r=void 0);let f=s===H&&n[p+1].startsWith("/>")?" ":"";o+=s===Y?d+Ai:h>=0?(t.push(c),d.slice(0,h)+gt+d.slice(h)+O+f):d+O+(h===-2?p:f)}return[wt(n,o+(n[e]||"<?>")+(i===2?"</svg>":i===3?"</math>":"")),t]},Q=class n{constructor({strings:i,_$litType$:e},t){let r;this.parts=[];let o=0,s=0,p=i.length-1,d=this.parts,[c,m]=Mi(i,e);if(this.el=n.createElement(c,t),N.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(r=N.nextNode())!==null&&d.length<p;){if(r.nodeType===1){if(r.hasAttributes())for(let h of r.getAttributeNames())if(h.endsWith(gt)){let v=m[s++],f=r.getAttribute(h).split(O),D=/([.?@])?(.*)/.exec(v);d.push({type:1,index:o,name:D[2],strings:f,ctor:D[1]==="."?qe:D[1]==="?"?Fe:D[1]==="@"?Ue:W}),r.removeAttribute(h)}else h.startsWith(O)&&(d.push({type:6,index:o}),r.removeAttribute(h));if(_t.test(r.tagName)){let h=r.textContent.split(O),v=h.length-1;if(v>0){r.textContent=ce?ce.emptyScript:"";for(let f=0;f<v;f++)r.append(h[f],X()),N.nextNode(),d.push({type:2,index:++o});r.append(h[v],X())}}}else if(r.nodeType===8)if(r.data===ft)d.push({type:2,index:o});else{let h=-1;for(;(h=r.data.indexOf(O,h+1))!==-1;)d.push({type:7,index:o}),h+=O.length-1}o++}}static createElement(i,e){let t=q.createElement("template");return t.innerHTML=i,t}};function U(n,i,e=n,t){if(i===S)return i;let r=t!==void 0?e._$Co?.[t]:e._$Cl,o=Z(i)?void 0:i._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),o===void 0?r=void 0:(r=new o(n),r._$AT(n,e,t)),t!==void 0?(e._$Co??=[])[t]=r:e._$Cl=r),r!==void 0&&(i=U(n,r._$AS(n,i.values),r,t)),i}var Ne=class{constructor(i,e){this._$AV=[],this._$AN=void 0,this._$AD=i,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(i){let{el:{content:e},parts:t}=this._$AD,r=(i?.creationScope??q).importNode(e,!0);N.currentNode=r;let o=N.nextNode(),s=0,p=0,d=t[0];for(;d!==void 0;){if(s===d.index){let c;d.type===2?c=new J(o,o.nextSibling,this,i):d.type===1?c=new d.ctor(o,d.name,d.strings,this,i):d.type===6&&(c=new We(o,this,i)),this._$AV.push(c),d=t[++p]}s!==d?.index&&(o=N.nextNode(),s++)}return N.currentNode=q,r}p(i){let e=0;for(let t of this._$AV)t!==void 0&&(t.strings!==void 0?(t._$AI(i,t,e),e+=t.strings.length-2):t._$AI(i[e])),e++}},J=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(i,e,t,r){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=i,this._$AB=e,this._$AM=t,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let i=this._$AA.parentNode,e=this._$AM;return e!==void 0&&i?.nodeType===11&&(i=e.parentNode),i}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(i,e=this){i=U(this,i,e),Z(i)?i===l||i==null||i===""?(this._$AH!==l&&this._$AR(),this._$AH=l):i!==this._$AH&&i!==S&&this._(i):i._$litType$!==void 0?this.$(i):i.nodeType!==void 0?this.T(i):Ii(i)?this.k(i):this._(i)}O(i){return this._$AA.parentNode.insertBefore(i,this._$AB)}T(i){this._$AH!==i&&(this._$AR(),this._$AH=this.O(i))}_(i){this._$AH!==l&&Z(this._$AH)?this._$AA.nextSibling.data=i:this.T(q.createTextNode(i)),this._$AH=i}$(i){let{values:e,_$litType$:t}=i,r=typeof t=="number"?this._$AC(i):(t.el===void 0&&(t.el=Q.createElement(wt(t.h,t.h[0]),this.options)),t);if(this._$AH?._$AD===r)this._$AH.p(e);else{let o=new Ne(r,this),s=o.u(this.options);o.p(e),this.T(s),this._$AH=o}}_$AC(i){let e=vt.get(i.strings);return e===void 0&&vt.set(i.strings,e=new Q(i)),e}k(i){Ke(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,t,r=0;for(let o of i)r===e.length?e.push(t=new n(this.O(X()),this.O(X()),this,this.options)):t=e[r],t._$AI(o),r++;r<e.length&&(this._$AR(t&&t._$AB.nextSibling,r),e.length=r)}_$AR(i=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);i!==this._$AB;){let t=pt(i).nextSibling;pt(i).remove(),i=t}}setConnected(i){this._$AM===void 0&&(this._$Cv=i,this._$AP?.(i))}},W=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(i,e,t,r,o){this.type=1,this._$AH=l,this._$AN=void 0,this.element=i,this.name=e,this._$AM=r,this.options=o,t.length>2||t[0]!==""||t[1]!==""?(this._$AH=Array(t.length-1).fill(new String),this.strings=t):this._$AH=l}_$AI(i,e=this,t,r){let o=this.strings,s=!1;if(o===void 0)i=U(this,i,e,0),s=!Z(i)||i!==this._$AH&&i!==S,s&&(this._$AH=i);else{let p=i,d,c;for(i=o[0],d=0;d<o.length-1;d++)c=U(this,p[t+d],e,d),c===S&&(c=this._$AH[d]),s||=!Z(c)||c!==this._$AH[d],c===l?i=l:i!==l&&(i+=(c??"")+o[d+1]),this._$AH[d]=c}s&&!r&&this.j(i)}j(i){i===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,i??"")}},qe=class extends W{constructor(){super(...arguments),this.type=3}j(i){this.element[this.name]=i===l?void 0:i}},Fe=class extends W{constructor(){super(...arguments),this.type=4}j(i){this.element.toggleAttribute(this.name,!!i&&i!==l)}},Ue=class extends W{constructor(i,e,t,r,o){super(i,e,t,r,o),this.type=5}_$AI(i,e=this){if((i=U(this,i,e,0)??l)===S)return;let t=this._$AH,r=i===l&&t!==l||i.capture!==t.capture||i.once!==t.once||i.passive!==t.passive,o=i!==l&&(t===l||r);r&&this.element.removeEventListener(this.name,this,t),o&&this.element.addEventListener(this.name,this,i),this._$AH=i}handleEvent(i){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,i):this._$AH.handleEvent(i)}},We=class{constructor(i,e,t){this.element=i,this.type=6,this._$AN=void 0,this._$AM=e,this.options=t}get _$AU(){return this._$AM._$AU}_$AI(i){U(this,i)}};var Li=Be.litHtmlPolyfillSupport;Li?.(Q,J),(Be.litHtmlVersions??=[]).push("3.3.3");var bt=(n,i,e)=>{let t=e?.renderBefore??i,r=t._$litPart$;if(r===void 0){let o=e?.renderBefore??null;t._$litPart$=r=new J(i.insertBefore(X(),o),o,void 0,e??{})}return r._$AI(n),r};var Ge=globalThis,g=class extends T{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let i=super.createRenderRoot();return this.renderOptions.renderBefore??=i.firstChild,i}update(i){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(i),this._$Do=bt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return S}};g._$litElement$=!0,g.finalized=!0,Ge.litElementHydrateSupport?.({LitElement:g});var Oi=Ge.litElementPolyfillSupport;Oi?.({LitElement:g});(Ge.litElementVersions??=[]).push("4.2.2");var yt={"panel.assign.action.discard_all":"Discard everything","panel.assign.action.review":"Review and confirm","panel.assign.action.review_hint":"Review and confirm the assignments","panel.assign.action.withdraw":"Withdraw this change","panel.assign.announce.applying":"The changes are being applied.","panel.assign.announce.armed":"Tap the destination group.","panel.assign.announce.discarded":"Every pending change has been discarded.","panel.assign.announce.drag_cancelled":"Drag cancelled.","panel.assign.announce.missing_travel":"Some covers have no travel.","panel.assign.announce.pending":"“{cover}” is pending, towards {target}. Nothing is written yet.","panel.assign.announce.reordered":"Order updated: it will be remembered.","panel.assign.announce.withdrawn":"“{cover}” goes back where it was: the change is withdrawn.","panel.assign.armed":"Tap the destination group for “{cover}”","panel.assign.drop_zone":"Take out of the profile — drop here","panel.assign.handle":"Move {cover} to another group, or reorder it","panel.assign.handle_hint":"Drag to assign or reorder, Enter to pick from a list","panel.assign.pending.all_own":"All values its own: nothing changes","panel.assign.pending.count":"{count} pending changes — nothing is written yet","panel.assign.pending.count_one":"1 pending change — nothing is written yet","panel.assign.pending.route":"{from} → {to}","panel.assign.pending.some_own":"Own values: those stay","panel.assign.target_none":"“No profile”","panel.assign.target_profile":"the profile “{profile}”","panel.banner.applying.body":"The covers are unavailable for a few seconds","panel.banner.applying.title":"The changes are being applied…","panel.banner.measuring.action.resume":"Resume the session","panel.banner.measuring.action.stop":"End it","panel.banner.measuring.body":"A guided calibration is using “{cover}”. Until the session ends, this panel only reads: nothing is written.","panel.banner.measuring.title":"Measurement in progress","panel.common.action.back":"Back","panel.common.action.cancel":"Cancel","panel.common.action.close":"Close","panel.common.action.configure":"Open Configure","panel.common.action.hide_all":"Hide the roll coefficients","panel.common.action.menu":"Open the Home Assistant menu","panel.common.action.retry":"Try again","panel.common.action.save":"Save","panel.common.action.show_all":"Show every value, roll coefficients included","panel.common.all_rooms":"All rooms","panel.common.gateway":"Gateway {gateway}","panel.common.loading":"Loading…","panel.common.not_yet":"This screen arrives in a later version. Until then “Configure” does everything it will do.","panel.common.opens_configure":"This opens the Configure dialog. The panel refreshes on its own when it closes.","panel.common.polling":"Live updates are not available on this version: the page refreshes on its own every 30 seconds.","panel.common.required":"This field cannot be left empty.","panel.common.room_filter":"Filter by room","panel.common.search":"Search for a cover","panel.common.unit.centimetres":"cm","panel.common.unit.seconds":"s","panel.detail.action.assign":"Assign to a profile…","panel.detail.action.correct":"Correct…","panel.detail.action.correct_note":"If it stops in the wrong place: times only, times and rolls, or the thorough calibration only","panel.detail.action.edit":"Edit the values by hand","panel.detail.action.measure_again":"Measure again","panel.detail.action.measure_again_note":"Full basic calibration, in the dialog","panel.detail.action.remove":"Remove the measurement…","panel.detail.action.thorough":"Thorough calibration","panel.detail.action.thorough_note":"On top: readings at 25 and 75 % per direction, and a check","panel.detail.action.travel":"Set the curtain travel…","panel.detail.correct.intro":"The correction opens the Configure dialog on the path chosen. When it comes back, the panel refreshes on its own.","panel.detail.correct.thorough":"Thorough calibration only","panel.detail.correct.thorough_note":"Readings at 25 and 75 % per direction, and a check","panel.detail.correct.times":"Times only","panel.detail.correct.times_note":"One run per direction, the rolls stay","panel.detail.correct.times_rolls":"Times and rolls","panel.detail.correct.times_rolls_note":"Full basic calibration","panel.detail.destination.defaults":"the default values","panel.detail.destination.file":"the values of the configuration file","panel.detail.destination.profile":"the values inherited from the profile “{profile}”","panel.detail.edit.action.save":"Save the values","panel.detail.edit.empty":"empty = nothing to say","panel.detail.edit.inherits":"inherits {value}","panel.detail.edit.intro":"These values count for this cover alone and beat both the profile and the file. A field left empty is not a zero: it means “nothing to say about this one”, and the value goes back to coming from the profile or from the file. Emptying every field is the same as removing the measurement.","panel.detail.edit.title":"Edit the values by hand","panel.detail.level_basic":"basic calibration","panel.detail.level_thorough":"thorough calibration","panel.detail.measured_at":"Measured on {date}","panel.detail.named":"Cover “{cover}”","panel.detail.remove.action":"Remove the measurement","panel.detail.remove.body":"The measurements made on “{cover}” will be removed and cannot be recovered. The cover will go back to using {destination}.","panel.detail.remove.title":"Remove the measurement?","panel.detail.remove.travel_stays":"The curtain travel stays: somebody measured it with a tape.","panel.detail.source.default":"default value","panel.detail.source.file":"from the configuration file","panel.detail.source.own":"own value, measured on this cover","panel.detail.source.profile":"inherited from the profile “{profile}”","panel.detail.title":"Cover detail","panel.detail.unknown":"This gateway has no cover with that identifier.","panel.detail.values.intro":"What the cover is using right now, value by value, with where it comes from: a value of its own always wins; then the assigned profile, then the file, then the defaults.","panel.detail.values.title":"Values in use","panel.detail.verify_note":"{deviation} cm out at the check","panel.dialog.option.current":"current","panel.dialog.option.none":"No profile","panel.dialog.option.none_meta":"Values from the configuration file, or the defaults. The travel and the values of its own stay.","panel.dialog.option.profile":"Profile “{profile}”","panel.dialog.option.profile_meta":"{travel} cm · ascent {opening} s · descent {closing} s","panel.dialog.subtitle":"“{cover}” — the choice stays pending until it is confirmed.","panel.dialog.title":"Which profile?","panel.error.not_found":"The panel could not read this gateway.","panel.firstrun.action.measure":"Measure a cover","panel.firstrun.body":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.firstrun.how":"A profile is not written, it is measured. Pick one representative cover and measure it once, with the guided calibration: about three minutes. Similar covers can then follow it.","panel.firstrun.note":"This opens the Configure dialog: that is where the measuring happens. When it is done, the profile appears here.","panel.firstrun.title":"No profile yet","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.cover.follows":"follows “{profile}”","panel.overview.cover.from_file":"The configuration file assigns this profile: it is changed there, not here.","panel.overview.cover.origin_adjusted":"Adjusted","panel.overview.cover.origin_inherited":"Inherited","panel.overview.cover.profile_missing":"The profile “{profile}” is no longer defined: this cover is running on its own configuration.","panel.overview.cover.travel":"travel {travel} cm","panel.overview.cover.travel_needed":"travel to be entered","panel.overview.cover.travel_unknown":"travel not recorded","panel.overview.explanation":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.overview.group.count":"{count} covers","panel.overview.group.count_one":"1 cover","panel.overview.group.empty":"No cover in this group.","panel.overview.group.from_file":"Defined in the configuration file, and read-only from here.","panel.overview.group.measured_on":"Measured on {cover} · {date}","panel.overview.group.measured_on_gone":"Measured on a cover this gateway no longer has · {date}","panel.overview.group.missing":"This profile is not defined any more: the covers below have quietly fallen back to their own configuration.","panel.overview.group.no_profile":"No profile","panel.overview.group.no_profile_note":"Values from the configuration file, or the defaults. It is not a fault: a cover with measurements of its own sits perfectly well here.","panel.overview.group.open":"Open the profile card","panel.overview.group.profile":"Profile “{profile}”","panel.overview.group.provenance_missing":"Where it was measured is not recorded.","panel.overview.group.values":"Reference travel {travel} cm · ascent {opening} s · descent {closing} s · slats {slat} s","panel.overview.group.values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.no_basic_covers":"Every cover of this gateway reports its own position, so there is no travel model to calibrate and nothing for this panel to do.","panel.overview.no_results":"No cover matches this search.","panel.overview.summary":"Profiles: {profiles} · Basic covers: {covers}","panel.overview.title":"Profiles and covers","panel.profile.action.delete":"Delete the profile…","panel.profile.action.edit":"Edit the values…","panel.profile.action.rename":"Rename…","panel.profile.delete.action":"Delete the profile","panel.profile.delete.affects":"It affects these covers:","panel.profile.delete.body":"They will go back to the values of the configuration file, where those exist, or to the defaults. Their travels and their own values stay. The profile's measurements cannot be recovered.","panel.profile.delete.title":"Delete the profile “{profile}”?","panel.profile.edit.action.save":"Apply to {count} covers","panel.profile.edit.action.save_one":"Apply to 1 cover","panel.profile.edit.intro":"A change to the profile changes everything for the covers that inherit its values, and only the inherited values for the adjusted ones: the values of their own stay, key by key.","panel.profile.edit.reach":"The change reaches {target}","panel.profile.edit.reach_all":"every one of the {count} covers that follow the profile","panel.profile.edit.reach_one":"1 cover","panel.profile.followers.adjusted":"adjusted: own values for {keys}","panel.profile.followers.count":"{count} covers follow it","panel.profile.followers.count_one":"1 cover follows it","panel.profile.followers.inherited":"inherited","panel.profile.followers.measured":"measured: nothing inherited","panel.profile.followers.none":"No cover follows it.","panel.profile.from_file":"Profile of the configuration file: read-only here.","panel.profile.impact.invalid":"correct the fields to see the preview","panel.profile.impact.kept":"own values stay: {keys}","panel.profile.impact.no_change":"no change: all values are its own","panel.profile.impact.no_travel":"travel not recorded: it will use the profile's values as they are","panel.profile.impact.state_adjusted":"adjusted: only the inherited values change","panel.profile.impact.state_inherited":"inherited: everything changes","panel.profile.impact.state_measured":"measured","panel.profile.impact.title":"Impact preview","panel.profile.name":"Profile “{profile}”","panel.profile.provenance":"Measured on {cover} · {date}","panel.profile.provenance_missing":"Where it was measured is not recorded.","panel.profile.provenance_now_none":"now follows no profile","panel.profile.provenance_now_profile":"now follows “{profile}”","panel.profile.reference_travel":"Reference travel","panel.profile.rename.action":"Rename","panel.profile.rename.field":"New name of the profile","panel.profile.rename.rule":"Letters, digits and underscores only: no spaces, no accents — the name is also a key of the configuration file. The rename follows every cover that uses the profile.","panel.profile.rename.title":"Rename the profile","panel.profile.stored":"Stored profile","panel.profile.title":"Profile card","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.profile.values":"Values of the profile","panel.review.action.back":"Back to the overview","panel.review.action.confirm":"Confirm {count} assignments","panel.review.action.confirm_one":"Confirm 1 assignment","panel.review.action.missing_travel":"{count} travels missing","panel.review.action.missing_travel_one":"1 travel missing","panel.review.after":"After","panel.review.before":"Before","panel.review.intro":"The changes are written all at once. For each cover, this is what it will really use: the profile's values brought to its own travel.","panel.review.note.all_own":"It has values of its own for everything: nothing changes. The profile would only count for values removed later on.","panel.review.note.back_to_defaults":"The default values come back: the position in per cent will be a rough estimate. The travel and any value of its own stay.","panel.review.note.back_to_file":"The values of the configuration file come back. The travel and any value of its own stay.","panel.review.note.scaled":"Values of the profile “{profile}” (measured on {reference} cm) brought to a travel of {travel} cm.","panel.review.note.some_own":"It has some values of its own: those stay. Only the inherited values change.","panel.review.title":"Review and confirm","panel.review.travel.aria":"Curtain travel in centimetres","panel.review.travel.hint":"A profile is the measurement of one cover with a certain travel, and it is brought to the others in proportion. The travel of these is not known: measure the distance the bottom edge covers from fully closed to fully open, and write it in centimetres (decimals with a comma or with a point).","panel.review.travel.label":"Curtain travel","panel.review.travel.placeholder":"e.g. 145","panel.review.travel.required":"The travel is needed, in centimetres.","panel.review.travel.title":"How far does the curtain of these covers run?","panel.screen.completed":"Completed","panel.screen.motor":"Motor","panel.screen.new_text":"new text — not translated yet","panel.screen.not_in_this_version":"This step belongs to the guided calibration, which moves into the panel in a later version.","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.position":"Estimated position","panel.screen.progress":"Positioning progress","panel.toast.action.undo":"Undo","panel.toast.assigned":"{count} assignments applied","panel.toast.assigned_one":"1 assignment applied","panel.toast.measure_removed":"Measurement removed: “{cover}” now uses {destination}.","panel.toast.order_saved":"The new order will be remembered.","panel.toast.profile_deleted":"Profile “{profile}” deleted: the covers go back to the file or to the defaults.","panel.toast.profile_renamed":"Renamed to “{profile}”: the rename follows every cover that uses it.","panel.toast.profile_saved":"Profile “{profile}” updated: {count} covers reached.","panel.toast.profile_saved_one":"Profile “{profile}” updated: 1 cover reached.","panel.toast.travel_saved":"The travel of “{cover}” is saved: the profile is brought to this measurement.","panel.toast.undone":"Changes undone: everything as it was.","panel.toast.values_saved":"The values of “{cover}” are saved: they beat the profile and the file."};var Ve=yt,En=Object.keys(Ve);var Di="/myhome_static/",Hi=/^!\[([^\]]*)\]\(([^)\s]+)\)$/;var he=n=>{let i=[];return n.split("**").forEach((t,r)=>{t&&i.push(r%2===1?a`<strong>${t}</strong>`:a`<span>${t}</span>`)}),i},Ni=n=>/^\s*[-*]\s+/.test(n),B=n=>{let i=(n||"").replace(/\r\n/g,`
`).split(/\n{2,}/),e=[];for(let t of i){let r=t.trim();if(!r)continue;let o=Hi.exec(r);if(o){e.push(o[2].startsWith(Di)?a`<img class="md-image" src=${o[2]} alt=${o[1]} />`:a`<p>${he(o[1])}</p>`);continue}let s=r.split(`
`);if(s.every(Ni)){e.push(a`<ul>
          ${s.map(p=>a`<li>${he(p.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}e.push(a`<p>
        ${s.map((p,d)=>d===0?he(p):[a`<br />`,...he(p)])}
      </p>`)}return a`${e}`};var C=n=>n&&typeof n=="object"&&"code"in n?n:{code:"unknown_error",message:String(n)},xt=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/overview",...i?{entry_id:i}:{}}),$t=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/texts",language:i}),kt=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_detail",entry_id:i,cover_unique_id:e}),ue=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/preview",entry_id:i,items:e,...t?{profile_values:t}:{}}),Rt=(n,i,e)=>n.subscribeMessage(e,{type:"myhome/calibration/subscribe",...i?{entry_id:i}:{}}),ee=n=>C(n).code==="unknown_command",Et=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/assign",entry_id:i,assignments:e,...t?{order:t}:{}}),Pt=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/reorder",entry_id:i,order:e,...t!==void 0?{profile:t}:{}}),Tt=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/set_travel",entry_id:i,cover_unique_id:e,height:t}),St=(n,i,e,t,r)=>n.sendMessagePromise({type:"myhome/calibration/cover_edit",entry_id:i,cover_unique_id:e,overrides:t,...r!==void 0?{height:r}:{}}),Ct=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_forget",entry_id:i,cover_unique_id:e}),At=(n,i,e,t,r)=>n.sendMessagePromise({type:"myhome/calibration/profile_edit",entry_id:i,name:e,values:t,reference_height:r}),It=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/profile_rename",entry_id:i,name:e,new_name:t}),Mt=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/profile_delete",entry_id:i,name:e}),Lt=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/undo",entry_id:i,undo_token:e});var Ye=(n,i)=>{if(!i)return n;let e=n;for(let[t,r]of Object.entries(i))e=e.split(`{${t}}`).join(String(r));return e},b=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this.language="en";this.loaded=!1}async load(i,e){let t=await $t(i,e);this._texts=t.texts??{},this.language=t.language,this.loaded=!0,this._numbers.clear(),this._dates=null}t(i,e){let t=this._lookup(i);if(t!==null)return Ye(t,e);let r=Ve[i];return Ye(r??i,e)}md(i,e){return B(this.t(i,e))}refusal(i,e){let t=i?this._lookup(`exceptions.${i}.message`):null;return t!==null?Ye(t,e):this.t("panel.error.not_found")}origin(i,e){return this.t(`selector.calibration_origin.options.${i}`,{profile:e??""})}number(i,e){let t=this._numbers.get(e);return t||(t=new Intl.NumberFormat(this.language,{minimumFractionDigits:e,maximumFractionDigits:e}),this._numbers.set(e,t)),t.format(i)}date(i){let e=new Date(i);return Number.isNaN(e.getTime())?i:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(e))}_lookup(i){let e=this._texts;for(let t of i.split(".")){if(e===null||typeof e!="object")return null;e=e[t]}return typeof e=="string"?e:null}};var Ot=n=>typeof customElements<"u"&&customElements.get(n)!==void 0;var zt=n=>{n.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var me=(n,i)=>{let e=ve(n.unique_id,i);return e?e.to:n.profile??null},ve=(n,i)=>i.find(e=>e.cover===n),Dt=(n,i,e)=>{let t=n.filter(r=>r.cover!==i.unique_id);return e===(i.profile??null)?{pending:t,withdrawn:!0}:{pending:[...t,{cover:i.unique_id,to:e}],withdrawn:!1}},Ht=(n,i)=>{let e=new Map(n.covers.map(o=>[o.unique_id,o]));if(!i)return[...n.covers].sort((o,s)=>o.order_index-s.order_index);let t=new Set,r=[];for(let o of i){let s=e.get(o);s&&!t.has(o)&&(t.add(o),r.push(s))}for(let o of n.covers)t.has(o.unique_id)||r.push(o);return r},Xe=(n,i,e)=>{let t=n.filter(o=>o!==i),r=t.length;if(e.beforeId){let o=t.indexOf(e.beforeId);r=o<0?t.length:o}else if(e.afterId){let o=t.indexOf(e.afterId);r=o<0?t.length:o+1}return[...t.slice(0,r),i,...t.slice(r)]},Nt=(n,i,e)=>{let t=e.filter(r=>r!==i).at(-1)??null;return Xe(n,i,{beforeId:null,afterId:t})},Ze=(n,i)=>n.map(e=>{let t=i[e.cover],r=t===void 0?void 0:A(t);return{cover_unique_id:e.cover,profile:e.to,...r==null?{}:{height:r}}}),A=n=>{let i=n.trim().replace(",",".");if(!i)return null;let e=Number(i);return Number.isFinite(e)?e:null},qi=20,Fi=500,te=n=>{if(n===void 0||n.trim()==="")return"missing_travel";let i=A(n);return i===null?"not_a_number":i<qi||i>Fi?"out_of_range":null},Qe=n=>({cover_unique_id:n.unique_id,profile:n.profile_from_file?null:n.profile??null}),qt=(n,i)=>i.to!==null&&n.height===null,I=["opening_time","closing_time","slat_time","opening_roll","closing_roll"],ie=["opening_time","closing_time","slat_time"],ge=["opening_roll","closing_roll"],x={opening_time:1,closing_time:1,slat_time:1,opening_roll:2,closing_roll:2};var M={opening_time:{min:1,max:600,decimals:1},closing_time:{min:1,max:600,decimals:1},slat_time:{min:0,max:60,decimals:1},opening_roll:{min:1,max:5,decimals:2},closing_roll:{min:1,max:5,decimals:2},height:{min:20,max:500,decimals:0},reference_height:{min:20,max:500,decimals:0}},fe={opening_time:"panel.common.unit.seconds",closing_time:"panel.common.unit.seconds",slat_time:"panel.common.unit.seconds",opening_roll:null,closing_roll:null,height:"panel.common.unit.centimetres",reference_height:"panel.common.unit.centimetres"},w=(n,i)=>{let e=(i??"").trim();if(e==="")return null;let t=A(e);if(t===null)return"not_a_number";let r=M[n];return r&&(t<r.min||t>r.max)?"out_of_range":null},$=n=>(n??"").trim()==="";var L="/config/integrations/integration/myhome";var Je="dialog-data-entry-flow",Ui=()=>typeof customElements<"u"&&customElements.get(Je)!==void 0,Ft=n=>{history.pushState(null,"",n),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))},Ut=n=>Ui()?(n.source.dispatchEvent(new CustomEvent("show-dialog",{bubbles:!0,composed:!0,detail:{dialogTag:Je,dialogImport:()=>Promise.resolve(),dialogParams:{startFlowHandler:n.entryId,domain:"myhome"}}})),setTimeout(()=>{document.querySelector(Je)||(n.onLeaving(),Ft(L))},400),"waiting"):(n.onLeaving(),Ft(L),"page");var Wi={view:"overview",params:{},path:"/"},Wt=n=>{let i="/"+(n||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(i==="/")return Wi;let e=i.slice(1).split("/"),t=e.slice(1).join("/"),r=t;try{r=decodeURIComponent(t)}catch{}return e[0]==="cover"&&t?{view:"cover",params:{id:r},path:i}:e[0]==="profile"&&t?{view:"profile",params:{name:r},path:i}:e[0]==="calibrate"&&t?{view:"calibrate",params:{session:r},path:i}:{view:"unknown",params:{},path:i}};var _e=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(i){this._onChange=i,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(i){let e=i||"/";if(e===this._fromHost)return;let t=this.current.path;this._fromHost=e,this.current.path!==t&&this._emit()}get current(){let i=typeof location<"u"?location.hash:"";return i&&i.length>1?Wt(i.slice(1)):Wt(this._fromHost)}navigate(i){let e="#"+(i.startsWith("/")?i:"/"+i);location.hash!==e&&(location.hash=e)}_emit(){this._onChange(this.current)}};var ne={for:null,answer:null,loading:!1,error:null,mode:"view",form:{},errors:{},preview:null,previewing:!1},re={for:null,mode:"view",form:{},errors:{},newName:"",nameError:"",impact:null,impacting:!1},F=n=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:n,search:"",room:"",announce:"",pending:[],order:null,drag:null,armed:null,dialog:null,review:!1,heights:{},heightsForced:!1,showAll:!1,preview:null,previewing:!1,applying:!1,snack:null,writeError:null,detail:ne,profile:re}),be={pending:[],order:null,heights:{},heightsForced:!1,preview:null,previewing:!1,review:!1,writeError:null},we=class{constructor(i){this._subscribers=new Set;this._state=F(i)}get state(){return this._state}subscribe(i){return this._subscribers.add(i),()=>this._subscribers.delete(i)}set(i){this._state={...this._state,...i};for(let e of this._subscribers)e(this._state)}setOverview(i){this.set({overview:i,entryId:i.entry_id,status:"ready",error:null})}setError(i){this.set({status:"error",error:i})}announce(i){this.set({announce:""}),this.set({announce:i})}};var k=u`:host{--myhome-text-on-primary: var(--text-primary-color, #ffffff);--myhome-snack-action: var(--snack-action-color, #ffc107);--myhome-primary: var(--primary-color, #03a9f4);--myhome-accent: var(--accent-color, #ff9800);--myhome-text: var(--primary-text-color, #212121);--myhome-text-soft: var(--secondary-text-color, #727272);--myhome-text-off: var(--disabled-text-color, #bdbdbd);--myhome-background: var(--primary-background-color, #fafafa);--myhome-background-soft: var(--secondary-background-color, #e5e5e5);--myhome-card: var(--card-background-color, #ffffff);--myhome-divider: var(--divider-color, rgba(0, 0, 0, .12));--myhome-error: var(--error-color, #db4437);--myhome-warning: var(--warning-color, #b26b00);--myhome-success: var(--success-color, #43a047);--myhome-info: var(--info-color, #039be5);--myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));--myhome-header-text: var(--app-header-text-color, #ffffff);--myhome-radius: var(--ha-card-border-radius, 12px);--myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, .14));--myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));--myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));--myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));--myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));--myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));--myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));--myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));--myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));--myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);display:block;min-height:100%;color:var(--myhome-text);background:var(--myhome-background)}*,*:before,*:after{box-sizing:border-box}:host * :focus-visible{outline:2px solid var(--myhome-primary);outline-offset:2px}@media(prefers-reduced-motion:reduce){:host *{animation-duration:.001ms!important;transition-duration:.001ms!important}}`,R=u`.card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}`,E=u`.cta{min-height:48px;padding:0 24px;border-radius:24px;border:none;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font:inherit;font-size:15px;font-weight:500;cursor:pointer}.cta.secondary{background:transparent;border:1px solid var(--myhome-primary);color:var(--myhome-primary)}.cta.text{background:transparent;border:none;color:var(--myhome-primary);padding:0 12px}.cta.destructive{background:var(--myhome-error-strong);color:var(--myhome-error)}.cta[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.cta.compact{min-height:44px;padding:0 18px;border-radius:22px;font-size:14px}`,z=u`.field{height:44px;border-radius:8px;border:1px solid var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text);padding:0 12px;font:inherit;font-size:14px}.field:disabled{color:var(--myhome-text-off)}`,ye=u`.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0}`;var Kt=n=>a`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${n}</div>`,oe=n=>{requestAnimationFrame(()=>{let i=n();i&&i.focus()})};var xe=class{constructor(){this._root=null;this._onKey=i=>{if(i.key!=="Tab"||!this._root)return;let e=Bt(this._root);if(e.length===0){i.preventDefault(),this._root.focus();return}let t=e[0],r=e[e.length-1],o=this._root.getRootNode().activeElement;i.shiftKey&&(o===t||o===this._root)?(i.preventDefault(),r.focus()):!i.shiftKey&&o===r&&(i.preventDefault(),t.focus())}}hold(i){this.release(),this._root=i,i.addEventListener("keydown",this._onKey),oe(()=>Bt(i)[0]??i)}release(){this._root?.removeEventListener("keydown",this._onKey),this._root=null}},Bt=n=>Array.from(n.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter(i=>i.offsetParent!==null||i===n);var jt=u`.measuring{max-width:1200px;margin:16px auto 0;padding:12px 16px;border-radius:var(--myhome-radius);background:var(--myhome-warning-pastel);display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.measuring strong{color:var(--myhome-warning);font-weight:500}.measuring .body{flex:1 1 320px;line-height:1.5}.measuring .links{display:flex;gap:16px}.measuring a{color:var(--myhome-primary);min-height:44px;display:inline-flex;align-items:center}`,Gt=(n,i,e)=>a`<div class="measuring" role="status" aria-live="polite">
    <strong>${n.t("panel.banner.measuring.title")}</strong>
    <span class="body">${n.t("panel.banner.measuring.body",{cover:i})}</span>
    <span class="links">
      <a href=${e}>${n.t("panel.banner.measuring.action.resume")}</a>
      <a href=${e}>${n.t("panel.banner.measuring.action.stop")}</a>
    </span>
  </div>`;var $e=u`.strip{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translate(-50%);max-width:92vw;box-sizing:border-box;box-shadow:var(--myhome-shadow)}.drop-zone{z-index:45;padding:14px 28px;min-height:48px;display:flex;align-items:center;border-radius:24px;font-size:14px;font-weight:500;border:2px dashed var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text-soft)}.drop-zone.over{border:2px solid var(--myhome-primary);color:var(--myhome-primary)}.dark{background:var(--myhome-text);color:var(--myhome-background);border-radius:8px;font-size:14px}.armed{z-index:40;padding:10px 16px;display:flex;gap:16px;align-items:center}.applying{z-index:70;padding:12px 20px}.applying .under{display:block;font-size:12px;opacity:.75;margin-top:2px}.snack{z-index:70;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:8px}.dark button{min-height:44px;padding:0 12px;border:none;background:transparent;color:var(--myhome-snack-action);font:inherit;font-weight:500;cursor:pointer}.pending-bar{z-index:30;background:var(--myhome-card);border:1px solid var(--myhome-divider);border-radius:28px;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.pending-bar .count{font-size:14px}.pending-bar .locked{font-size:13px;color:var(--myhome-warning);flex-basis:100%}.pending-bar button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.pending-bar .discard{padding:0 12px;background:transparent;color:var(--myhome-text-soft)}.pending-bar .review{padding:0 20px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.pending-bar button[disabled]{color:var(--myhome-text-off);background:var(--myhome-background-soft);cursor:default}@media(max-width:599px){.strip.pending-bar{left:8px;right:8px;transform:none;max-width:none;justify-content:space-between}.strip.pending-bar .count{flex-basis:100%}}`,Vt=(n,i)=>a`<div class="strip drop-zone ${i?"over":""}" data-group="none">
    ${n.t("panel.assign.drop_zone")}
  </div>`,Yt=(n,i,e)=>a`<div class="strip dark armed" role="status">
    <span>${n.t("panel.assign.armed",{cover:i})}</span>
    <button type="button" @click=${e}>${n.t("panel.common.action.cancel")}</button>
  </div>`,Xt=n=>{let{i18n:i}=n;return a`<div class="strip pending-bar">
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
    ${n.locked?a`<span class="locked"
          >${i.t("panel.banner.measuring.body",{cover:n.lockedCover})}</span
        >`:l}
  </div>`},ke=n=>a`<div class="strip dark applying" role="status">
    ${n.t("panel.banner.applying.title")}
    <span class="under">${n.t("panel.banner.applying.body")}</span>
  </div>`,Re=(n,i,e)=>a`<div class="strip dark snack" role="status">
    <span>${i}</span>
    ${e?a`<button type="button" @click=${e}>
          ${n.t("panel.toast.action.undo")}
        </button>`:l}
  </div>`;var Zt=n=>{let i=new Map;for(let e of n.querySelectorAll("[data-row]")){let t=e.getBoundingClientRect();i.set(e.getAttribute("data-row")??"",{top:t.top,left:t.left})}return i},Qt=(n,i)=>{if(!Bi())for(let e of n.querySelectorAll("[data-row]")){let t=i.get(e.getAttribute("data-row")??"");if(!t)continue;let r=e.getBoundingClientRect(),o=t.left-r.left,s=t.top-r.top;if(Math.abs(o)<1&&Math.abs(s)<1)continue;e.style.transition="none",e.style.transform=`translate(${o}px, ${s}px)`,e.offsetHeight,e.style.transition="transform 220ms ease",e.style.transform="";let p=()=>{e.style.transition="",e.removeEventListener("transitionend",p)};e.addEventListener("transitionend",p)}},Bi=()=>typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches;var Ee=class{constructor(i){this._start=null;this._longPress=null;this._pressedAt=null;this._ghost=null;this._target=null;this._scroll=null;this._edge=0;this._scroller=null;this._clearLongPressOnce=()=>this._clearLongPress();this._onPressMove=i=>{let e=this._pressedAt;e&&Math.hypot(i.clientX-e.x,i.clientY-e.y)<12||this._clearLongPress()};this._onMove=i=>{let e=this._start;if(!e)return;if(!e.live){if(Math.hypot(i.clientX-e.x,i.clientY-e.y)<6)return;e.live=!0,this._callbacks.onStart(e.cover)}this._moveGhost(i.clientX,i.clientY),this._autoScroll(i.clientX,i.clientY);let t=this._targetAt(i.clientX,i.clientY,e.cover);Ki(t,this._target)||(this._target=t,this._callbacks.onOver(t))};this._onUp=()=>this._finish(!0);this._onCancel=()=>this._finish(!1);this._callbacks=i}get dragging(){return this._start?.live?this._start.cover:null}press(i,e){if(!this._callbacks.blocked()){if(this._callbacks.narrow()){this._arm(i,e);return}e.preventDefault(),this._start={cover:i,x:e.clientX,y:e.clientY,live:!1},window.addEventListener("pointermove",this._onMove),window.addEventListener("pointerup",this._onUp),window.addEventListener("pointercancel",this._onCancel),window.addEventListener("blur",this._onCancel)}}arm(i,e){this._callbacks.blocked()||this._arm(i,e)}cancel(){if(this._start?.live){this._finish(!1);return}this._clear()}stop(){this._clear(),this._clearLongPress()}_arm(i,e){this._clearLongPress(),this._pressedAt=e?{x:e.clientX,y:e.clientY}:null,this._longPress=setTimeout(()=>{this._longPress=null,this._callbacks.onArm(i)},450),window.addEventListener("pointerup",this._clearLongPressOnce),window.addEventListener("pointermove",this._onPressMove),window.addEventListener("pointercancel",this._clearLongPressOnce),window.addEventListener("blur",this._clearLongPressOnce)}_clearLongPress(){this._longPress&&(clearTimeout(this._longPress),this._longPress=null),this._pressedAt=null,window.removeEventListener("pointerup",this._clearLongPressOnce),window.removeEventListener("pointermove",this._onPressMove),window.removeEventListener("pointercancel",this._clearLongPressOnce),window.removeEventListener("blur",this._clearLongPressOnce)}_finish(i){let e=this._start?.live??!1;this._clear(),e&&this._callbacks.onEnd(i)}_clear(){window.removeEventListener("pointermove",this._onMove),window.removeEventListener("pointerup",this._onUp),window.removeEventListener("pointercancel",this._onCancel),window.removeEventListener("blur",this._onCancel),this._start=null,this._target=null,this._stopScrolling(),this._ghost?.remove(),this._ghost=null}ghost(i,e){let t=document.createElement("div");t.className="drag-ghost",t.setAttribute("aria-hidden","true"),t.textContent=i,e.appendChild(t),this._ghost=t}_moveGhost(i,e){this._ghost&&(this._ghost.style.transform=`translate(${i+12}px, ${e+8}px)`)}_autoScroll(i,e){let t=this._callbacks.root().querySelector(".groups");if(!t||t.scrollWidth<=t.clientWidth){this._stopScrolling();return}let r=t.getBoundingClientRect(),o=i<r.left+64?-1:i>r.right-64?1:0;if(this._edge=o,this._scroller=t,o===0){this._stopScrolling();return}if(this._scroll===null){let s=()=>{this._edge===0||!this._scroller||(this._scroller.scrollLeft+=this._edge*14,this._scroll=requestAnimationFrame(s))};this._scroll=requestAnimationFrame(s)}}_stopScrolling(){this._edge=0,this._scroll!==null&&(cancelAnimationFrame(this._scroll),this._scroll=null)}_targetAt(i,e,t){let r=this._callbacks.root().elementFromPoint(i,e),o=r?.closest?.("[data-group]");if(!o)return null;let s=o.getAttribute("data-group")??"",p=r?.closest?.("[data-row]"),d=p?.getAttribute("data-row")??null;if(!p||!d||d===t)return{group:s,beforeId:null,afterId:null,end:!0};let c=p.getBoundingClientRect();return e<c.top+c.height/2?{group:s,beforeId:d,afterId:null,end:!1}:{group:s,beforeId:null,afterId:d,end:!1}}},Ki=(n,i)=>n===null||i===null?n===i:n.group===i.group&&n.beforeId===i.beforeId&&n.afterId===i.afterId;var Pe=u`.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.chip.measured{background:var(--myhome-primary-pastel);color:var(--myhome-text)}.chip.adjusted{background:var(--myhome-accent-pastel);color:var(--myhome-text)}.chip .dot{width:6px;height:6px;border-radius:3px;background:var(--myhome-accent);display:inline-block}`,Te=(n,i,e,t)=>{let r=i==="measured"?"measured":i==="adjusted"?"adjusted":"neutral",o;return t&&i==="inherited"?o=n.t("panel.overview.cover.origin_inherited"):t&&i==="adjusted"?o=n.t("panel.overview.cover.origin_adjusted"):o=n.origin(i,e),a`<span class="chip ${r}"
    >${r==="adjusted"?a`<span class="dot" aria-hidden="true"></span>`:l}${o}</span
  >`};var Jt=u`.row{position:relative;display:flex;align-items:flex-start;gap:8px;padding:8px;border-radius:8px;min-height:48px;-webkit-user-select:none;-webkit-touch-callout:none}.row .divider{position:absolute;left:8px;right:8px;top:-1px;height:1px;background:var(--myhome-divider);opacity:.6;pointer-events:none}.row .insert-line{position:absolute;left:8px;right:8px;top:-2px;height:3px;border-radius:2px;background:var(--myhome-primary);pointer-events:none}.row .pending-outline{position:absolute;inset:0;border:2px dashed var(--myhome-primary);border-radius:8px;pointer-events:none}.row .source-veil{position:absolute;inset:0;background:var(--myhome-background-soft);opacity:.7;border-radius:8px;pointer-events:none}.row .handle{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);cursor:grab;font-size:18px;letter-spacing:2px;border-radius:8px;touch-action:none;-webkit-user-select:none;user-select:none}.row .handle[disabled]{cursor:default;color:var(--myhome-text-off)}@media(max-width:599px){.row .handle{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.row .handle:focus-visible{position:static;width:48px;height:48px;margin:0;overflow:visible;clip-path:none}}.row .body{flex:1 1 auto;min-width:0}.row .main{display:block;width:100%;text-align:left;border:none;background:transparent;color:inherit;font:inherit;cursor:pointer;padding:2px 0;border-radius:6px}.row .name{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:14.5px;line-height:1.35}.row .sub{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.row .chips:empty{display:none}.row .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}.row .warn{display:block;font-size:12.5px;color:var(--myhome-warning);margin-top:4px}.route{display:inline-flex;align-items:center;gap:2px;font-size:12px;color:var(--myhome-primary);background:var(--myhome-primary-faint);border:1px dashed var(--myhome-primary);border-radius:10px;padding:2px 2px 2px 8px;max-width:100%}.route .text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.route .withdraw{width:48px;height:48px;margin:-14px -14px -14px 0;display:inline-flex;align-items:center;justify-content:center;border:none;background:transparent;color:inherit;font:inherit;font-size:14px;line-height:1;cursor:pointer;border-radius:24px}.row .note{display:block;font-size:12.5px;color:var(--myhome-info);margin-top:4px}`,ji=(n,i,e)=>{let t=i.height!==null?n.t("panel.overview.cover.travel",{travel:n.number(i.height,0)}):e?n.t("panel.overview.cover.travel_needed"):n.t("panel.overview.cover.travel_unknown");return i.area?`${i.area} · ${t}`:t},Gi=(n,i)=>i.has_own.length===0?"":I.every(e=>i.has_own.includes(e))?n.t("panel.assign.pending.all_own"):n.t("panel.assign.pending.some_own"),ei=(n,i)=>{let{i18n:e,pending:t}=i,r=!!t&&t.to!==null&&n.height===null,o=t?Gi(e,n):"",s=`chips-${n.unique_id}`;return a`<div class="row" data-row=${n.unique_id}>
    ${i.insertBefore?a`<div class="insert-line" aria-hidden="true"></div>`:i.first?l:a`<div class="divider" aria-hidden="true"></div>`}
    ${t?a`<div class="pending-outline" aria-hidden="true"></div>`:l}
    ${i.dragging?a`<div class="source-veil" aria-hidden="true"></div>`:l}
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
      <button class="main" type="button" title=${n.name} aria-describedby=${s}
        @click=${()=>i.onOpen(n)}>
        <span class="name">${n.name}</span>
        <span class="sub">${ji(e,n,r)}</span>
        ${o?a`<span class="note">${o}</span>`:l}
        ${n.profile_missing?a`<span class="warn"
              >${e.t("panel.overview.cover.profile_missing",{profile:n.profile??""})}</span
            >`:l}
        ${n.profile_from_file&&!n.profile_missing?a`<span class="sub">${e.t("panel.overview.cover.from_file")}</span>`:l}
      </button>
      <div class="chips" id=${s}>
        ${Te(e,n.origin,n.profile,i.short)}
        ${t?a`<span class="route">
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
  </div>`};var ti=u`.backdrop{position:fixed;inset:0;background:#0006;z-index:60}.dialog{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(440px,92vw);max-height:80vh;overflow:auto;background:var(--myhome-card);color:var(--myhome-text);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);z-index:61;padding:20px;box-sizing:border-box}.dialog h2{margin:0 0 4px;font-size:18px;font-weight:500}.dialog .subtitle{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft)}.dialog .options{display:flex;flex-direction:column;gap:8px}.dialog .option{text-align:left;border-radius:8px;font:inherit;padding:12px;min-height:48px;cursor:pointer;border:1px solid var(--myhome-divider);background:transparent;color:inherit}.dialog .option.current{border-color:var(--myhome-primary);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.dialog .option .line{display:flex;align-items:baseline;gap:8px}.dialog .option .title{font-weight:500;flex:1}.dialog .option .tag{font-size:12.5px;color:var(--myhome-primary)}.dialog .option .meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.dialog .foot{display:flex;justify-content:flex-end;margin-top:12px}.dialog .foot button{min-height:44px;padding:0 16px;border:none;background:transparent;color:var(--myhome-text-soft);font:inherit;font-size:14px;cursor:pointer}`,Vi=(n,i)=>i.missing||i.values.opening_time===void 0?n.t("panel.overview.group.values_unknown"):n.t("panel.dialog.option.profile_meta",{travel:i.reference_height===null?"?":n.number(i.reference_height,0),opening:n.number(i.values.opening_time,1),closing:n.number(i.values.closing_time,1)}),ii=n=>{let{i18n:i}=n,e=(t,r,o)=>a`<button
    class="option ${n.current===t?"current":""}"
    type="button"
    aria-current=${n.current===t?"true":l}
    @click=${()=>n.onPick(t)}
  >
    <span class="line"
      ><span class="title">${r}</span
      >${n.current===t?a`<span class="tag">${i.t("panel.dialog.option.current")}</span>`:l}</span
    >
    <span class="meta">${o}</span>
  </button>`;return a`
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
        ${n.profiles.map(t=>e(t.name,i.t("panel.dialog.option.profile",{profile:t.name}),Vi(i,t)))}
        ${e(null,i.t("panel.dialog.option.none"),i.t("panel.dialog.option.none_meta"))}
      </div>
      <div class="foot">
        <button type="button" @click=${n.onClose}>
          ${i.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `};var ni=u`.groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(300px,1fr);gap:16px;align-items:start;overflow-x:auto;padding-bottom:8px;overscroll-behavior-x:contain}}.group{position:relative;background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.group-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider)}.group-head .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.group-head h2{margin:0;font-size:17px;font-weight:500;flex:1 1 auto;min-width:0}.group-head h2 button{border:none;background:transparent;color:var(--myhome-primary);font:inherit;cursor:pointer;padding:0;min-height:28px;text-align:left}.group-head .count{color:var(--myhome-text-soft);font-size:13px}.group-head .meta{margin:6px 0 0;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}.group-head .meta.second{margin-top:4px}.group-head .meta.warn{color:var(--myhome-warning)}.group-body{display:flex;flex-direction:column;padding:8px;gap:2px;min-height:56px}.group-body .empty{margin:8px;font-size:13px;color:var(--myhome-text-soft)}.group-body .insert-end{margin:0 8px;height:3px;border-radius:2px;background:var(--myhome-primary);pointer-events:none}.group .over,.group .armed-target{position:absolute;inset:0;border-radius:var(--myhome-radius);pointer-events:none}.group .over{border:2px solid var(--myhome-primary)}.group .armed-target{border:2px dashed var(--myhome-primary)}.group.collapsed .group-head{border-bottom:none;min-height:48px;cursor:pointer}`,et=n=>n===null?"none":`profile:${n}`,ri=n=>n==="none"?null:n.slice(8),oi=(n,i)=>{let{i18n:e}=i,t=n.covers.length===1?e.t("panel.overview.group.count_one"):e.t("panel.overview.group.count",{count:n.covers.length}),r=i.collapsed;return a`<section
    class="group ${r?"collapsed":""}"
    data-group=${et(n.key)}
    aria-labelledby=${n.id}
  >
    <div
      class="group-head"
      @click=${()=>{r&&i.onTarget(n.key)}}
    >
      <div class="line">
        <h2 id=${n.id}>
          ${n.key===null?n.title:a`<button
                type="button"
                title=${r?e.t("panel.assign.armed",{cover:""}):e.t("panel.overview.group.open")}
                @click=${o=>{if(o.stopPropagation(),r){i.onTarget(n.key);return}i.onOpenProfile(n.key)}}
              >
                ${n.title}
              </button>`}
        </h2>
        <span class="count">${t}</span>
      </div>
      ${n.values&&!r?a`<p class="meta">${n.values}</p>`:l}
      ${r?l:n.warning?a`<p class="meta second warn">${n.warning}</p>`:n.provenance?a`<p class="meta second">${n.provenance}</p>`:l}
    </div>
    ${r?l:a`<div class="group-body">
          ${n.covers.map((o,s)=>ei(o,{i18n:e,short:o.profile===n.key,first:s===0,pending:i.pending.find(p=>p.cover===o.unique_id),route:i.route(o),locked:i.locked,insertBefore:i.insertBefore===o.unique_id,dragging:i.dragging===o.unique_id,onOpen:i.onOpenCover,onGrab:i.onGrab,onRowPress:i.onRowPress,onPick:i.onPick,onWithdraw:i.onWithdraw}))}
          ${i.insertEnd?a`<div class="insert-end" aria-hidden="true"></div>`:l}
          ${n.covers.length===0?a`<p class="empty">${e.t("panel.overview.group.empty")}</p>`:l}
        </div>`}
    ${i.over?a`<div class="over" aria-hidden="true"></div>`:l}
    ${r?a`<div class="armed-target" aria-hidden="true"></div>`:l}
  </section>`};var ai=u`.sheet-backdrop{position:fixed;inset:0;background:#0006;z-index:50}.sheet{position:fixed;left:0;right:0;bottom:0;max-height:86vh;background:var(--myhome-card);color:var(--myhome-text);z-index:51;border-radius:16px 16px 0 0;box-shadow:var(--myhome-shadow);display:flex;flex-direction:column}@media(min-width:600px){.sheet{inset:0 0 0 auto;width:min(480px,100vw);max-height:none;border-radius:0}}.sheet .head{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--myhome-divider)}.sheet .head h2{margin:0;font-size:18px;font-weight:500;flex:1}.sheet .head button{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);font-size:20px;cursor:pointer;border-radius:24px}.sheet .body[aria-busy=true] table,.sheet .body[aria-busy=true] .note{opacity:.55;transition:opacity .12s ease}.sheet .body{flex:1;overflow:auto;padding:16px}.sheet .intro{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .travel-note{background:var(--myhome-info-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}.sheet .travel-note strong{font-weight:500;display:block;margin-bottom:4px}.sheet .item{border:1px solid var(--myhome-divider);border-radius:8px;padding:12px;margin:0 0 12px}.sheet .item .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.sheet .item .name{font-weight:500;flex:1 1 auto;min-width:0}.sheet .item .route{font-size:13px;color:var(--myhome-text-soft)}.sheet label.travel{display:flex;align-items:center;gap:8px;margin:10px 0 2px;font-size:13.5px}.sheet label.travel .what{flex:1}.sheet label.travel input{width:96px;height:44px;border-radius:8px;border:1px solid var(--myhome-divider);background:var(--myhome-card);color:inherit;padding:0 10px;font:inherit;font-size:14px;text-align:right}.sheet label.travel input[aria-invalid=true]{border-color:var(--myhome-error)}.sheet .field-error{margin:2px 0 0;font-size:12.5px;color:var(--myhome-error);text-align:right}.sheet table{width:100%;border-collapse:collapse;margin:10px 0 0;font-size:13.5px}.sheet th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}.sheet th.what{text-align:left}.sheet th.after{font-weight:500;color:var(--myhome-text)}.sheet td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}.sheet td.what{text-align:left;color:var(--myhome-text-soft)}.sheet td.after{font-weight:500}.sheet .note{margin:10px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .problem{margin:10px 0 0;font-size:12.5px;color:var(--myhome-error);line-height:1.5}.sheet .show-all{border:none;background:transparent;color:var(--myhome-primary);font:inherit;font-size:13.5px;cursor:pointer;padding:4px 0;min-height:44px}.sheet .refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 12px;font-size:13.5px;line-height:1.5}.sheet .foot{padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));border-top:1px solid var(--myhome-divider);display:flex;gap:12px;justify-content:flex-end}.sheet .foot button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.sheet .foot .back{padding:0 16px;background:transparent;color:var(--myhome-text-soft)}.sheet .foot .confirm{padding:0 24px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.sheet .foot .confirm[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}`,Yi=(n,i,e,t,r)=>{if(I.every(s=>i.has_own.includes(s)))return n.t("panel.review.note.all_own");if(i.has_own.length>0)return n.t("panel.review.note.some_own");if(e.to===null)return t?.origin==="from_the_file"?n.t("panel.review.note.back_to_file"):n.t("panel.review.note.back_to_defaults");let o=r.get(e.to);return!t||t.height===null||!o||o.reference_height===null?"":n.t("panel.review.note.scaled",{profile:e.to,reference:n.number(o.reference_height,0),travel:n.number(t.height,0)})},si=(n,i,e,t)=>n.refusal(e,{cover:i.name,covers:i.name,count:1,profile:t.to??"",key:n.t("panel.review.travel.label"),min:20,max:500}),li=n=>{let{i18n:i}=n,e=new Map((n.preview??[]).map(p=>[p.cover_unique_id,p])),t=n.pending.map(p=>({change:p,cover:n.covers.get(p.cover)})).filter(p=>p.cover!==void 0),r=t.filter(({change:p,cover:d})=>p.to!==null&&d.height===null&&te(n.heights[p.cover])!==null).length,o=n.showAll?[...ie,...ge]:ie,s=p=>i.t(`options.step.calibration_edit.data.${p}`);return a`
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
    <aside
      class="sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-title"
      data-focus-root
    >
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
        ${n.refusal?a`<div class="refusal" role="alert">${n.refusal}</div>`:l}
        ${r>0?a`<div class="travel-note">
              <strong>${i.t("panel.review.travel.title")}</strong>
              ${i.t("panel.review.travel.hint")}
            </div>`:l}
        ${t.map(({change:p,cover:d})=>{let c=e.get(p.cover),m=n.heights[p.cover],h=p.to!==null&&d.height===null,v=h?te(m):null,f=v!==null&&(n.forced||(m??"")!==""),D=c&&c.problem===null?o.filter(_=>c.values[_]!==void 0&&d.values[_]!==void 0):[];return a`<section class="item">
            <div class="line">
              <span class="name">${d.name}</span>
              <span class="route">${n.route(d)}</span>
            </div>
            ${h?a`<label class="travel">
                    <span class="what">${i.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${m??""}
                      ?disabled=${n.applying}
                      aria-label=${i.t("panel.review.travel.aria")}
                      aria-invalid=${f?"true":"false"}
                      placeholder=${i.t("panel.review.travel.placeholder")}
                      @input=${_=>n.onHeight(p.cover,_.target.value)}
                    />
                    <span>${i.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${f?a`<p class="field-error">
                        ${v==="missing_travel"?i.t("panel.review.travel.required"):si(i,d,v,p)}
                      </p>`:l}`:l}
            ${c&&c.problem!==null&&c.problem!=="missing_travel"?a`<p class="problem">
                  ${si(i,d,c.problem,p)}
                </p>`:l}
            ${D.length>0?a`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${i.t("panel.review.before")}</th>
                      <th class="after">${i.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${D.map(_=>a`<tr>
                        <td class="what">${s(_)}</td>
                        <td>${i.number(d.values[_],x[_]??1)}</td>
                        <td class="after">
                          ${i.number(c.values[_],x[_]??1)}
                        </td>
                      </tr>`)}
                  </tbody>
                </table>`:l}
            ${(()=>{let _=Yi(i,d,p,c,n.profiles);return _?a`<p class="note">${_}</p>`:l})()}
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
    </aside>
  `};var Se=class extends g{constructor(){super();this._trap=new xe;this._returnTo=null;this._returnToRow=null;this._onKey=e=>{if(e.key==="Escape"){if(this.state.drag){this._drag.cancel();return}if(this.state.armed){this.actions.arm(null);return}if(this.state.dialog){this.actions.dialog(null);return}this.state.review&&!this.state.applying&&this.actions.review(!1)}};this._flip=null;this._narrowQuery=typeof matchMedia=="function"?matchMedia("(max-width: 599px)"):null;this._onWidth=()=>this.requestUpdate();this._route=e=>{let t=ve(e.unique_id,this.state.pending);return t?this.i18n.t("panel.assign.pending.route",{from:this._groupName(e.profile??null),to:this._groupName(t.to)}):""};this._onGrab=(e,t)=>{this._drag.press(e.unique_id,t)};this._onRowPress=(e,t)=>{this._narrow&&!this._locked&&this._drag.arm(e.unique_id,t)};this.i18n=new b,this.state=F({view:"overview",params:{},path:"/"}),this.actions={},this._drag=new Ee({root:()=>this.renderRoot,blocked:()=>this._locked,narrow:()=>this._narrow,onArm:e=>{let t=this._cover(e);t&&this.actions.arm(t)},onStart:e=>{let t=this._cover(e);t&&(this._drag.ghost(t.name,this.renderRoot),this.actions.drag(t))},onOver:e=>this.actions.over(e),onEnd:e=>this._endDrag(e)})}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[k,R,E,z,Pe,Jt,ni,$e,ti,ai,u`:host{display:block;background:transparent}.intro{margin:8px 0 4px;max-width:72ch}.intro p{margin:0 0 8px;line-height:1.55}.counts{margin:0 0 16px;color:var(--myhome-text-soft)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.controls .search{flex:1 1 220px;max-width:340px}.controls .spacer{flex:1 1 auto}.select-wrap{position:relative;display:inline-flex}.select-wrap:after{content:"";position:absolute;right:13px;top:50%;width:7px;height:7px;border-right:1.6px solid var(--myhome-text-soft);border-bottom:1.6px solid var(--myhome-text-soft);border-radius:1px;transform:translateY(-70%) rotate(45deg);pointer-events:none}select.field{appearance:none;padding-right:36px}a.cta{display:inline-flex;align-items:center;text-decoration:none}.welcome{max-width:640px;margin:48px auto;padding:32px}.welcome h2{margin:0 0 12px;font-size:22px;font-weight:500}.welcome p{margin:0 0 8px;line-height:1.55}.welcome .soft{color:var(--myhome-text-soft);margin-bottom:24px}.welcome .after{margin:12px 0 0;font-size:13px;color:var(--myhome-text-soft)}.notice{padding:16px;margin:16px 0;font-size:14px;line-height:1.55}.notice .actions{margin-top:12px}.groups{margin-bottom:96px}.drag-ghost{position:fixed;left:0;top:0;z-index:80;pointer-events:none;background:var(--myhome-card);color:var(--myhome-text);border:1px solid var(--myhome-primary);border-radius:8px;box-shadow:var(--myhome-shadow);padding:10px 14px;font-size:14px;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}`]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey),this._narrowQuery?.addEventListener("change",this._onWidth)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._narrowQuery?.removeEventListener("change",this._onWidth),this._drag.stop(),this._trap.release()}updated(e){if(this._locked){let t=this._drag.dragging!==null;this._drag.stop(),t&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"))}if(e.has("state")){let t=e.get("state");if(this._manageFocus(t),this._flip){let r=this._flip;this._flip=null,requestAnimationFrame(()=>Qt(this.renderRoot,r))}}}_beforeMove(){this._flip=Zt(this.renderRoot)}_manageFocus(e){let t=this.state.dialog!==null||this.state.review,r=(e?.dialog??null)!==null||(e?.review??!1);if(t&&!r){let o=this._activeElement();this._returnTo=o,this._returnToRow=o?.closest("[data-row]")?.getAttribute("data-row")??null,requestAnimationFrame(()=>{let s=this.renderRoot.querySelector("[data-focus-root]");s&&this._trap.hold(s)});return}if(!t&&r){this._trap.release();let o=this._returnTo,s=this._returnToRow;this._returnTo=null,this._returnToRow=null,requestAnimationFrame(()=>{((s?this.renderRoot.querySelector(`[data-row="${CSS.escape(s)}"] .handle`):null)??(o?.isConnected?o:null))?.focus()})}}_activeElement(){let e=this.renderRoot.activeElement;return e instanceof HTMLElement?e:null}get _overview(){return this.state.overview}get _locked(){return this._overview?.measuring!=null||this.state.applying}get _narrow(){return this._narrowQuery?.matches??!1}_cover(e){return this._overview?.covers.find(t=>t.unique_id===e)}get _covers(){let e=this._overview;return e?Ht(e,this.state.order):[]}get _rooms(){let e=new Set;for(let t of this._overview?.covers??[])t.area&&e.add(t.area);return Array.from(e).sort((t,r)=>t.localeCompare(r,this.i18n.language))}_matches(e){let t=this.state.search.trim().toLowerCase();return t&&!e.name.toLowerCase().includes(t)?!1:!this.state.room||e.area===this.state.room}_groupName(e){return e===null?this.i18n.t("panel.overview.group.no_profile"):this.i18n.t("panel.overview.group.profile",{profile:e})}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group.values_unknown"):this.i18n.t("panel.overview.group.values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),opening:this.i18n.number(e.values.opening_time,1),closing:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml")return this.i18n.t("panel.overview.group.from_file");if(!e.measured_on)return this.i18n.t("panel.overview.group.provenance_missing");let t=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.group.measured_on_gone",{date:t});let r=this.i18n.t("panel.overview.group.measured_on",{cover:e.measured_on_name,date:t}),o=(this._overview?.covers??[]).find(s=>s.unique_id===e.measured_on);if(o&&o.profile!==e.name){let s=o.profile??this.i18n.t("panel.overview.group.no_profile");r+=` · ${this.i18n.t("panel.profile.provenance_now_profile",{profile:s})}`}return r}get _groups(){let e=this._overview;if(!e)return[];let t=this._covers,r=s=>t.filter(p=>me(p,this.state.pending)===s&&this._matches(p)),o=e.profiles.map((s,p)=>({key:s.name,id:`group-${p}`,title:this.i18n.t("panel.overview.group.profile",{profile:s.name}),values:this._valuesLine(s),provenance:this._provenanceLine(s),warning:s.missing?this.i18n.t("panel.overview.group.missing"):"",covers:r(s.name)}));return o.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group.no_profile"),values:this.i18n.t("panel.overview.group.no_profile_note"),provenance:"",warning:"",covers:r(null)}),o}_appendAtEnd(e,t){if(this.state.order===null||t===(e.profile??null))return;let r=this._covers;this.actions.setOrder(Nt(r.map(o=>o.unique_id),e.unique_id,r.filter(o=>me(o,this.state.pending)===t).map(o=>o.unique_id)))}_endDrag(e){let t=this.state,r=t.drag,o=r?.insert??null,s=r?.over??null,p=r?this._cover(r.cover):void 0;if(this.actions.drag(null),!e||!p||s===null){r&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));return}let d=ri(s),c=this._covers.map(f=>f.unique_id),m=Xe(c,p.unique_id,o??{beforeId:null,afterId:null});this._beforeMove();let h=ve(p.unique_id,t.pending),v=h?h.to:p.profile??null;if(d!==v){this.actions.setOrder(m),this.actions.assign(p,d);return}if(t.pending.length>0){this.actions.setOrder(m),this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));return}this.actions.reorder(m)}_renderControls(){return a`<div class="controls">
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
    </section>`}_renderStrips(){let e=this.state;if(e.drag)return Vt(this.i18n,e.drag.over==="none");if(e.armed){let t=this._cover(e.armed);return Yt(this.i18n,t?.name??"",()=>this.actions.arm(null))}return e.applying?ke(this.i18n):e.snack?Re(this.i18n,e.snack.message,e.snack.undoToken?()=>this.actions.undo():null):e.pending.length>0&&!e.review?Xt({i18n:this.i18n,count:e.pending.length,locked:this._locked,lockedCover:this._overview?.measuring?.name??"",onDiscard:()=>{this._beforeMove(),this.actions.discardAll()},onReview:()=>this.actions.review(!0)}):l}_renderDialog(){let e=this.state.dialog?this._cover(this.state.dialog):void 0;return e?ii({i18n:this.i18n,cover:e,profiles:this._overview?.profiles??[],current:me(e,this.state.pending),onPick:t=>{this._beforeMove(),this._appendAtEnd(e,t),this.actions.assign(e,t)},onClose:()=>this.actions.dialog(null)}):l}_renderReview(){let e=this._overview;return!this.state.review||!e?l:li({i18n:this.i18n,pending:this.state.pending,covers:new Map(e.covers.map(t=>[t.unique_id,t])),profiles:new Map(e.profiles.map(t=>[t.name,t])),preview:this.state.preview,previewing:this.state.previewing,heights:this.state.heights,forced:this.state.heightsForced,showAll:this.state.showAll,applying:this.state.applying,refusal:this.state.writeError?this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{}):"",route:this._route,onHeight:(t,r)=>this.actions.height(t,r),onToggleShowAll:()=>this.actions.toggleShowAll(),onConfirm:()=>this.actions.confirm(),onClose:()=>this.actions.review(!1)})}render(){let e=this._overview;if(!e)return a`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return a`<div class="card notice">
        ${B(this.i18n.t("panel.overview.no_basic_covers"))}
      </div>`;if(e.profiles.length===0)return this._renderFirstRun();let t=this._groups,r=t.reduce((p,d)=>p+d.covers.length,0),o=this.state.search.trim()!==""||this.state.room!=="",s=this.state.drag;return a`
      <div class="intro">${this.i18n.md("panel.overview.explanation")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.summary",{profiles:e.profiles.length,covers:e.covers.length})}
      </p>
      ${this._renderControls()}
      ${r===0&&o?a`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${()=>this.actions.clearFilters()}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`:a`<div class="groups">
            ${t.map(p=>{let d=et(p.key),c=s?.insert??null,m=c!==null&&c.group===d;return oi(p,{i18n:this.i18n,pending:this.state.pending,route:this._route,locked:this._locked,collapsed:this.state.armed!==null,over:s?.over===d,insertBefore:m?c.beforeId:null,insertEnd:m?c.end||c.afterId===p.covers.at(-1)?.unique_id:!1,dragging:s?.cover??null,onOpenProfile:h=>this.actions.openProfile(h),onOpenCover:h=>this.actions.openCover(h.unique_id),onGrab:this._onGrab,onRowPress:this._onRowPress,onPick:h=>this.actions.dialog(h),onWithdraw:h=>{this._beforeMove(),this.actions.withdraw(h)},onTarget:h=>{let v=this.state.armed?this._cover(this.state.armed):void 0;v&&(this._beforeMove(),this._appendAtEnd(v,h),this.actions.assign(v,h))}})})}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",Se);var Ce=u`:host{display:block}.card{padding:16px;margin:0 0 16px;max-width:720px}h2{margin:0 0 4px;font-size:16px;font-weight:500}h2:focus-visible{outline:2px solid var(--myhome-primary);outline-offset:4px}.sub{margin:0;font-size:13px;color:var(--myhome-text-soft)}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}.intro{margin:0 0 12px;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}table[aria-busy=true],.rows[aria-busy=true]{opacity:.55;transition:opacity .12s ease}.rows{display:flex;flex-direction:column}.row{display:flex;align-items:baseline;gap:8px;padding:8px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.row .what{flex:1 1 150px;color:var(--myhome-text-soft)}.row .value{font-variant-numeric:tabular-nums;font-weight:500}.row .from{flex-basis:100%;font-size:12px;color:var(--myhome-text-soft);text-align:right}.row .instead{font-size:12px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}h3{margin:16px 0 4px;font-size:14px;font-weight:500}.actions{display:flex;flex-direction:column;gap:8px}.wide{min-height:48px;border:none;border-radius:8px;background:var(--myhome-primary-faint);color:var(--myhome-primary);font:inherit;font-size:14px;cursor:pointer;text-align:left;padding:10px 14px;display:block;width:100%}.wide.destructive{background:var(--myhome-error-strong);color:var(--myhome-error)}.wide[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.wide .note{display:block;color:var(--myhome-text-soft);font-size:12.5px;margin-top:2px}.warn{background:var(--myhome-warning-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13px;line-height:1.5}.warn strong{font-weight:500;display:block;margin-bottom:4px}.danger{background:var(--myhome-error-pastel);border-radius:8px;padding:16px;font-size:14px;line-height:1.55}.danger strong{font-weight:500}.danger p{margin:8px 0 0}.danger ul{margin:4px 0 0;padding:0 0 0 20px;line-height:1.7}.danger .soft{color:var(--myhome-text-soft);font-size:13px}.fields{display:flex;flex-direction:column;gap:10px}label.field-row{display:flex;align-items:center;gap:8px;font-size:13.5px}label.field-row .what{flex:1}label.field-row input{width:110px;text-align:right}label.field-row .unit{color:var(--myhome-text-soft);width:24px}.field[aria-invalid=true]{border-color:var(--myhome-error)}.field-error{margin:2px 26px 0 0;font-size:12.5px;color:var(--myhome-error);text-align:right}.foot{display:flex;gap:12px;justify-content:flex-end;margin-top:16px}table{width:100%;border-collapse:collapse;margin:16px 0 0;font-size:13.5px}th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}th.what,td.what{text-align:left}th.after{font-weight:500;color:var(--myhome-text)}td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}td.what{color:var(--myhome-text-soft)}td.after{font-weight:500}a{color:var(--myhome-primary)}.refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}`,se=(n,i,e,t,r)=>a`<div class="row">
  <span class="what">${n}</span>
  <span class="value">${i}${e?a` ${e}`:l}</span>
  ${r?a`<span class="instead">${r}</span>`:l}
  ${t?a`<span class="from">${t}</span>`:l}
</div>`,ae=n=>a`<div>
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
  ${n.error?a`<p class="field-error">${n.error}</p>`:l}
</div>`,y=n=>a`<button
  class="wide ${n.destructive?"destructive":""}"
  type="button"
  title=${n.title??""}
  ?disabled=${n.disabled??!1}
  @click=${n.onClick}
>
  ${n.label}
  ${n.note?a`<span class="note">${n.note}</span>`:l}
</button>`,P=(n,i,e,t=!1)=>a`<div class="foot">
  <button class="cta text" type="button" ?disabled=${t} @click=${i}>
    ${n}
  </button>
  ${e}
</div>`;var K=[...ie,...ge],Ae=class extends g{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)){if(this.state.detail.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new b,this.state=F({view:"cover",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[k,R,E,z,Pe,Ce]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.detail,t=`${e.for??""}|${e.mode}`;if(t===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=t,oe(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}_label(e){return this.i18n.t(`options.step.calibration_edit.data.${e}`)}_unit(e){let t=fe[e];return t?this.i18n.t(t):""}_number(e,t){return this.i18n.number(t,x[e]??M[e]?.decimals??1)}_problem(e,t){return this.i18n.refusal(t,{key:this._label(e),min:M[e]?.min??0,max:M[e]?.max??0,cover:this.state.detail.answer?.cover.name??""})}_destination(){let e=this.state.detail.answer?.forget;return e?e.falls_back_to==="profile"?this.i18n.t("panel.detail.destination.profile",{profile:e.profile??""}):e.falls_back_to==="file"?this.i18n.t("panel.detail.destination.file"):this.i18n.t("panel.detail.destination.defaults"):""}render(){let e=this.state.detail;return e.loading?a`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`:e.answer?a`${this._head(e.answer.cover)}
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
        ${P(this.i18n.t("panel.common.action.retry"),this.actions.retry,a`<button class="cta secondary compact" type="button" @click=${this.actions.back}>
            ${this.i18n.t("panel.common.action.back")}
          </button>`)}
      </div>`}_head(e){let t=[e.area,e.height===null?this.i18n.t("panel.overview.cover.travel_unknown"):this.i18n.t("panel.overview.cover.travel",{travel:this.i18n.number(e.height,0)}),e.profile?this.i18n.t("panel.overview.cover.follows",{profile:e.profile}):null].filter(o=>!!o),r=e.level==="precise"?this.i18n.t("panel.detail.level_thorough"):e.level==="basic"?this.i18n.t("panel.detail.level_basic"):null;return a`<section class="card">
      <p class="sub">${t.join(" · ")}</p>
      <div class="chips">
        ${Te(this.i18n,e.origin,e.profile,!1)}
        ${e.measured_at?a`<span class="chip"
              >${this.i18n.t("panel.detail.measured_at",{date:this.i18n.date(e.measured_at)})}${r?` · ${r}`:""}</span
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
    </section>`}_view(e,t){let r=K.map(p=>t.find(d=>d.key===p)).filter(p=>p!==void 0),o=e.has_own.length>0,s=o&&e.level!=="precise";return a`<section class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.values.title")}</h2>
        <p class="intro">${this.i18n.t("panel.detail.values.intro")}</p>
        <div class="rows">
          ${r.map(p=>this._valueRow(e,p))}
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
      </section>`}_valueRow(e,t){let r=t.origin==="own"?this.i18n.t("panel.detail.source.own"):t.origin==="profile"?this.i18n.t("panel.detail.source.profile",{profile:e.profile??""}):t.origin==="file"?this.i18n.t("panel.detail.source.file"):this.i18n.t("panel.detail.source.default");return se(this._label(t.key),this._number(t.key,t.value),this._unit(t.key),r,t.own&&t.inherited_value!==null?this.i18n.t("panel.detail.edit.inherits",{value:this._number(t.key,t.inherited_value)}):null)}_flowButton(e,t){return y({label:`${this.i18n.t(e)} ↗`,note:this.i18n.t(t),title:this.i18n.t("panel.common.opens_configure"),onClick:r=>this.actions.openFlow(r.currentTarget)})}_edit(e){let t=this.state.detail.form,r=K.map(s=>e.find(p=>p.key===s)).filter(s=>s!==void 0),o=r.some(s=>w(s.key,t[s.key])!==null);return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.edit.title")}</h2>
      <div class="warn">${this.i18n.t("panel.detail.edit.intro")}</div>
      <div class="fields">
        ${r.map(s=>this._field(s))}
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||o}
          @click=${this.actions.saveValues}>
          ${this.i18n.t("panel.detail.edit.action.save")}
        </button>`,this.state.applying)}
    </section>`}_field(e){let t=this.state.detail.form[e.key],r=w(e.key,t),o=e.inherited_value===null?this.i18n.t("panel.detail.edit.empty"):this.i18n.t("panel.detail.edit.inherits",{value:this._number(e.key,e.inherited_value)});return ae({label:this._label(e.key),value:t??"",unit:this._unit(e.key),placeholder:o,error:r?this._problem(e.key,r):null,disabled:this.state.applying,onInput:s=>this.actions.field(e.key,s)})}_travel(e){let t=this.state.detail.form.height,r=w("height",t),o=this.state.detail.preview,s=o&&o.problem===null?K.filter(p=>o.values[p]!==void 0&&e.values[p]!==void 0):[];return a`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("options.step.calibration_edit.data.height")}
      </h2>
      <p class="intro">
        ${this.i18n.t("options.step.calibration_edit.data_description.height")}
      </p>
      ${ae({label:this.i18n.t("panel.review.travel.label"),ariaLabel:this.i18n.t("panel.review.travel.aria"),value:t??"",unit:this.i18n.t("panel.common.unit.centimetres"),placeholder:this.i18n.t("panel.review.travel.placeholder"),error:r?this._problem("height",r):null,disabled:this.state.applying,onInput:p=>this.actions.field("height",p)})}
      ${o&&o.problem!==null?a`<p class="field-error">${this._problem("height",o.problem)}</p>`:l}
      ${s.length>0?a`<table aria-busy=${this.state.detail.previewing?"true":"false"}>
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
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||r!==null||$(t)}
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
    </section>`}_remove(e){let t=this.state.detail.answer?.forget;return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.remove.title")}</h2>
      <div class="danger">
        <p style="margin:0">
          ${this.i18n.t("panel.detail.remove.body",{cover:e.name,destination:this._destination()})}
        </p>
        ${t?.travel_stays?a`<p class="soft">${this.i18n.t("panel.detail.remove.travel_stays")}</p>`:l}
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.detail.remove.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-cover-detail")||customElements.define("myhome-cover-detail",Ae);var j=["reference_height",...I],Xi=/^[A-Za-z0-9_]+$/,Ie=class extends g{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)){if(this.state.profile.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new b,this.state=F({view:"profile",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[k,R,E,z,Ce]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.profile,t=`${e.for??""}|${e.mode}`;if(t===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=t,oe(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}get _profile(){let e=this.state.profile.for;return this.state.overview?.profiles.find(t=>t.name===e)??null}get _followers(){let e=this._profile,t=this.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return t.filter(o=>r.has(o.unique_id))}_label(e){return e==="reference_height"?this.i18n.t("panel.profile.reference_travel"):this.i18n.t(`options.step.profile_edit.data.${e}`)}_unit(e){let t=fe[e];return t?this.i18n.t(t):""}_number(e,t){return this.i18n.number(t,x[e]??M[e]?.decimals??1)}_problem(e,t){return this.i18n.refusal(t,{key:this._label(e),min:M[e]?.min??0,max:M[e]?.max??0})}_ownKeys(e){return e.has_own.map(t=>this.i18n.t(`options.step.calibration_edit.data.${t}`)).join(", ")}render(){let e=this._profile;if(!this.state.overview)return a`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;if(!e)return a`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.unknown")}</h2>
        ${P(this.i18n.t("panel.common.action.back"),this.actions.back,l)}
      </div>`;let t=this.state.profile.mode;return a`${this._head(e)}
    ${this.state.writeError?a`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:l}
    ${t==="view"?this._view(e):l}
    ${t==="edit"?this._edit():l}
    ${t==="rename"?this._rename(e):l}
    ${t==="delete"?this._delete(e):l}`}_head(e){let r=(this.state.overview?.covers??[]).find(p=>p.unique_id===e.measured_on),o;e.measured_on&&e.measured_on_name&&e.measured_at?(o=this.i18n.t("panel.profile.provenance",{cover:e.measured_on_name,date:this.i18n.date(e.measured_at)}),r&&r.profile!==e.name&&(o+=` · ${r.profile?this.i18n.t("panel.profile.provenance_now_profile",{profile:r.profile}):this.i18n.t("panel.profile.provenance_now_none")}`)):e.measured_on&&e.measured_at?o=this.i18n.t("panel.overview.group.measured_on_gone",{date:this.i18n.date(e.measured_at)}):o=this.i18n.t("panel.profile.provenance_missing");let s=e.editable?this.i18n.t("panel.profile.stored"):this.i18n.t("panel.profile.from_file");return a`<section class="card">
      <p class="sub">${e.missing?o:`${s} · ${o}`}</p>
      ${e.missing?a`<p class="warn" style="margin:12px 0 0">
            ${this.i18n.t("panel.overview.group.values_unknown")}
          </p>`:l}
    </section>`}_view(e){let t=this._followers;return a`${e.missing?l:a`<section class="card">
            <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.values")}</h2>
            <div class="rows">
              ${j.map(r=>r==="reference_height"?e.reference_height===null?l:se(this._label(r),this._number(r,e.reference_height),this._unit(r),"",null):e.values[r]===void 0?l:se(this._label(r),this._number(r,e.values[r]),this._unit(r),"",null))}
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
      ${e.editable?a`<section class="card actions">
            ${y({label:this.i18n.t("panel.profile.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
            ${y({label:this.i18n.t("panel.profile.action.rename"),disabled:this._locked,onClick:()=>this.actions.mode("rename")})}
            ${y({label:this.i18n.t("panel.profile.action.delete"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("delete")})}
          </section>`:l}`}_follower(e){let r=I.every(o=>e.has_own.includes(o))?this.i18n.t("panel.profile.followers.measured"):e.has_own.length>0?this.i18n.t("panel.profile.followers.adjusted",{keys:this._ownKeys(e)}):this.i18n.t("panel.profile.followers.inherited");return a`<div class="row">
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
      ${e.profile_from_file?a`<span class="from">${this.i18n.t("panel.overview.cover.from_file")}</span>`:l}
    </div>`}_edit(){let e=this._followers,t=this.state.profile.form,r=j.some(s=>w(s,t[s])!==null||$(t[s])),o=e.length===1?this.i18n.t("panel.profile.edit.reach_one"):this.i18n.t("panel.profile.edit.reach_all",{count:e.length});return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.action.edit")}</h2>
      <div class="warn">
        <strong>${this.i18n.t("panel.profile.edit.reach",{target:o})}</strong>
        ${this.i18n.t("panel.profile.edit.intro")}
      </div>
      <div class="fields">
        ${j.map(s=>ae({label:this._label(s),value:t[s]??"",unit:this._unit(s),error:$(t[s])?this.i18n.t("panel.common.required"):(()=>{let p=w(s,t[s]);return p?this._problem(s,p):null})(),disabled:this.state.applying,onInput:p=>this.actions.field(s,p)}))}
      </div>
      <h3>${this.i18n.t("panel.profile.impact.title")}</h3>
      <div class="rows" aria-busy=${this.state.profile.impacting?"true":"false"}>
        ${e.map(s=>this._impact(s,r))}
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||r}
          @click=${this.actions.saveValues}>
          ${e.length===1?this.i18n.t("panel.profile.edit.action.save_one"):this.i18n.t("panel.profile.edit.action.save",{count:e.length})}
        </button>`,this.state.applying)}
    </section>`}_impact(e,t){let r=I.every(p=>e.has_own.includes(p)),o=r?this.i18n.t("panel.profile.impact.state_measured"):e.has_own.length>0?this.i18n.t("panel.profile.impact.state_adjusted"):this.i18n.t("panel.profile.impact.state_inherited"),s;if(r)s=this.i18n.t("panel.profile.impact.no_change");else if(e.height===null)s=this.i18n.t("panel.profile.impact.no_travel");else if(t)s=this.i18n.t("panel.profile.impact.invalid");else{let p=(this.state.profile.impact??[]).find(d=>d.cover_unique_id===e.unique_id);if(!p||p.problem!==null)s=this.i18n.t("panel.common.loading");else if(s=I.filter(c=>!e.has_own.includes(c)&&e.values[c]!==void 0&&p.values[c]!==void 0).map(c=>`${this.i18n.t(`options.step.calibration_edit.data.${c}`)} ${this._number(c,e.values[c])} → ${this._number(c,p.values[c])}`).join(" · "),e.has_own.length>0){let c=this.i18n.t("panel.profile.impact.kept",{keys:this._ownKeys(e)});s=s?`${s} — ${c}`:c}}return a`<div class="row">
      <span class="what">${e.name}</span>
      <span class="instead">${o}</span>
      <span class="from" style="text-align:left">${s}</span>
    </div>`}_rename(e){let t=this.state.profile.newName,r=t.trim()!==""&&!Xi.test(t.trim()),o=r?this.i18n.refusal("invalid_name",{profile:t}):this.state.profile.nameError;return a`<section class="card">
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
          @input=${s=>this.actions.newName(s.target.value)}
        />
      </label>
      ${o?a`<p class="field-error" style="text-align:left">${o}</p>`:l}
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||r||t.trim()===""||t.trim()===e.name}
          @click=${this.actions.rename}>
          ${this.i18n.t("panel.profile.rename.action")}
        </button>`,this.state.applying)}
    </section>`}_delete(e){let t=this._followers;return a`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("panel.profile.delete.title",{profile:e.name})}
      </h2>
      <div class="danger">
        ${t.length===0?a`<p style="margin:0">${this.i18n.t("panel.profile.followers.none")}</p>`:a`<p style="margin:0">${this.i18n.t("panel.profile.delete.affects")}</p>
              <ul>
                ${t.map(r=>a`<li>${r.name}</li>`)}
              </ul>`}
        <p>${this.i18n.t("panel.profile.delete.body")}</p>
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.profile.delete.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-profile-card")||customElements.define("myhome-profile-card",Ie);var pi={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},di=n=>(...i)=>({_$litDirective$:n,values:i}),Me=class{constructor(i){}get _$AU(){return this._$AM._$AU}_$AT(i,e,t){this._$Ct=i,this._$AM=e,this._$Ci=t}_$AS(i,e){return this.update(i,e)}update(i,e){return this.render(...e)}};var ci="important",Zi=" !"+ci,hi=di(class extends Me{constructor(n){if(super(n),n.type!==pi.ATTRIBUTE||n.name!=="style"||n.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(n){return Object.keys(n).reduce((i,e)=>{let t=n[e];return t==null?i:i+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${t};`},"")}update(n,[i]){let{style:e}=n.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(i)),this.render(i);for(let t of this.ft)i[t]==null&&(this.ft.delete(t),t.includes("-")?e.removeProperty(t):e[t]=null);for(let t in i){let r=i[t];if(r!=null){this.ft.add(t);let o=typeof r=="string"&&r.endsWith(Zi);t.includes("-")||o?e.setProperty(t,o?r.slice(0,-11):r,o?ci:""):e[t]=r}}return S}});var ui=(n,i)=>n.summary?.note?a`<div class="stub">${n.summary.note}</div>`:l;var mi=(n,i)=>{let e=n.options??[];return e.length===0?l:a`<div class="options" role="group" aria-label=${n.title}>
    ${e.map(t=>a`<button
        class="option"
        type="button"
        aria-pressed=${t.current?"true":"false"}
        @click=${()=>i.fire(t.action)}
      >
        <span class="option-head">
          <strong class="option-title">${t.title}</strong>
          ${t.chip?a`<span class="chip neutral">${t.chip}</span>`:l}
        </span>
        ${t.meta?a`<span class="option-meta">${t.meta}</span>`:l}
      </button>`)}
  </div>`};var vi=(n,i)=>{let e=n.progress;if(!e)return a`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`;let t=Math.max(0,Math.min(1,e.fraction))*100;return a`<div class="progress-card">
    ${e.text?a`<p class="instruction">${e.text}</p>`:l}
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
  </div>`};var gi=(n,i)=>{let e=n.press;if(!e)return a`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`;let t=e.state==="moving";return a`
    ${e.instruction?a`<p class="instruction">${e.instruction}</p>`:l}
    <div class="live">
      <div class="live-row">
        <span class="name">${i.i18n.t("panel.screen.motor")}</span>
        <span class="value ${t?"moving":""}">${e.motor??""}</span>
      </div>
      ${e.position?a`<div class="live-row">
            <span class="name">${i.i18n.t("panel.screen.position")}</span>
            <span class="value">${e.position}</span>
          </div>`:l}
    </div>
    ${e.note?a`<div
          class="note ${e.state==="problem"?"error":"success"}"
          role=${e.state==="problem"?"alert":"status"}
        >
          ${e.note}
        </div>`:l}
  `};var fi=(n,i)=>{let e=n.options??[];if(e.length===0&&!n.field)return a`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`;let t=n.field;return a`
    <div class="options" role="group" aria-label=${n.title}>
      ${e.map(r=>a`<button
          class="option"
          type="button"
          aria-pressed=${r.current?"true":"false"}
          @click=${()=>i.fire(r.action)}
        >
          <strong class="option-title">${r.title}</strong>
          ${r.meta?a`<span class="option-meta">${r.meta}</span>`:l}
        </button>`)}
    </div>
    ${t?a`<div class="reading" style="margin-top:12px">
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
            ${t.unit?a`<span class="unit">${t.unit}</span>`:l}
          </div>
          ${t.error?a`<p class="error" id="gap-error" role="alert">${t.error}</p>`:l}
        </div>`:l}
  `};var Qi=n=>{let i=[n.hint?"reading-hint":"",n.error?"reading-error":""].filter(e=>e!=="");return i.length>0?i.join(" "):void 0},_i=(n,i)=>{let e=n.field;return e?a`<div class="reading ${e.big===!1?"":"big"}">
    <label for="reading">${e.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${e.value}
        placeholder=${e.placeholder??""}
        aria-describedby=${Qi(e)??l}
        aria-invalid=${e.error?"true":"false"}
        @input=${t=>i.fire("field",t.target.value)}
      />
      ${e.unit?a`<span class="unit">${e.unit}</span>`:l}
    </div>
    ${e.hint?a`<p class="hint" id="reading-hint">${e.hint}</p>`:l}
    ${e.error?a`<p class="error" id="reading-error" role="alert">${e.error}</p>`:l}
  </div>`:a`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`};var wi=(n,i)=>{let e=n.summary;return e?a`
    <div class="summary">
      ${e.rows.map(t=>a`<div class="summary-row">
          <span class="label">${t.label}</span>
          ${t.before?a`<span class="before" aria-label=${i.i18n.t("panel.review.before")}
                >${t.before}</span
              >`:l}
          <span class="after" aria-label=${i.i18n.t("panel.review.after")}>${t.after}</span>
        </div>`)}
      ${e.note?a`<p class="note-line">${e.note}</p>`:l}
    </div>
    ${e.code?a`<pre class="code">${e.code}</pre>`:l}
  `:a`<div class="stub">${i.i18n.t("panel.screen.not_in_this_version")}</div>`};var bi=(n,i)=>n.summary?.rows?.length?a`<div class="summary">
    ${n.summary.rows.map(e=>a`<div class="summary-row">
        <span class="label">${e.label}</span>
        <span class="after">${e.after}</span>
      </div>`)}
    ${n.summary.note?a`<p class="note-line">${n.summary.note}</p>`:l}
  </div>`:l;var yi=u`.text-column{min-width:0}.phase{margin:0 0 8px;font-size:12px;color:var(--myhome-text-soft)}.new-text{display:inline-block;margin:0 0 12px;background:var(--myhome-info-pastel);border-radius:10px;padding:3px 10px;font-size:12px;color:var(--myhome-text-soft)}.screen-title{margin:0 0 12px;font-size:20px;font-weight:500;line-height:1.3;display:flex;align-items:center;gap:10px}.outcome-icon{width:32px;height:32px;flex:0 0 32px;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;font-weight:600}.outcome-icon.saved{background:var(--myhome-success-pastel);color:var(--myhome-success)}.outcome-icon.saved:before{content:"\2713"}.outcome-icon.cancelled{background:var(--myhome-error-pastel);color:var(--myhome-error)}.outcome-icon.cancelled:before{content:"\2715"}.outcome-icon.expired{background:var(--myhome-warning-pastel);color:var(--myhome-warning)}.outcome-icon.expired:before{content:"\29d7"}.outcome-icon.problem{background:var(--myhome-error-pastel);color:var(--myhome-error)}.outcome-icon.problem:before{content:"!"}.drawing{height:230px;border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);margin:0 0 16px;background-color:var(--myhome-drawing-paper);background-repeat:no-repeat}.prose p{margin:0 0 12px;font-size:14.5px;line-height:1.6;text-wrap:pretty}.prose ul{margin:0 0 12px;padding-left:20px;font-size:14.5px;line-height:1.6}.prose .md-image{display:block;max-width:100%;border-radius:var(--myhome-radius);margin:0 0 12px}.big{width:100%;min-height:64px;border:none;border-radius:16px;font:inherit;font-size:16px;font-weight:600;cursor:pointer;background:var(--myhome-primary);color:var(--myhome-text-on-primary);box-shadow:var(--myhome-shadow)}.big.moving{background:var(--myhome-accent);color:var(--myhome-text)}.big[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default;box-shadow:none}.options{display:flex;flex-direction:column;gap:8px;margin:4px 0 0}.option{text-align:left;border-radius:10px;font:inherit;padding:14px;min-height:56px;cursor:pointer;color:inherit;border:1px solid var(--myhome-divider);background:var(--myhome-card)}.option[aria-pressed=true]{border-color:var(--myhome-primary);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.option .option-head{display:flex;align-items:center;gap:8px}.option .option-title{font-weight:500;flex:1;font-size:14.5px;line-height:1.4}.option .option-meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:3px}.live{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:14px 16px;display:flex;flex-direction:column;gap:8px;font-size:14px}.live-row{display:flex;justify-content:space-between;gap:12px}.live-row .name{color:var(--myhome-text-soft)}.live-row .value{font-variant-numeric:tabular-nums;font-weight:500}.live-row .value.moving{color:var(--myhome-warning);animation:myhome-pulse 1.2s ease-in-out infinite}@keyframes myhome-pulse{0%,to{opacity:1}50%{opacity:.55}}.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.instruction{margin:0 0 16px;font-size:16.5px;line-height:1.5;font-weight:500}.note{margin:14px 0 0;border-radius:8px;padding:12px 14px;font-size:14px;line-height:1.55}.note.success{background:var(--myhome-success-pastel)}.note.error{background:var(--myhome-error-pastel)}.note.info{background:var(--myhome-info-pastel)}.progress-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px}.progress-track{height:8px;border-radius:4px;background:var(--myhome-background-soft);overflow:hidden}.progress-bar{height:100%;background:var(--myhome-primary);border-radius:4px;transition:width .1s linear}.progress-eta{margin:10px 0 0;font-size:13px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}.reading{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:4px 0 0}.reading label{display:block;font-size:13.5px;margin:0 0 8px}.reading .row{display:flex;align-items:center;gap:10px}.reading input{flex:1;min-width:0;height:56px;border-radius:10px;border:1px solid var(--myhome-divider);background:var(--myhome-card);color:inherit;padding:0 14px;font:inherit;font-size:26px;font-variant-numeric:tabular-nums}.reading.big input{height:64px;font-size:32px}.reading .unit{font-size:16px;color:var(--myhome-text-soft)}.reading.big .unit{font-size:18px}.reading .hint{margin:8px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.reading .error{margin:8px 0 0;font-size:12.5px;color:var(--myhome-error);line-height:1.5}.summary{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:8px 16px;margin:4px 0 14px}.summary-row{display:flex;align-items:baseline;gap:8px;padding:9px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.summary-row:last-of-type{border-bottom:none}.summary-row .label{flex:1 1 130px;color:var(--myhome-text-soft)}.summary-row .before{color:var(--myhome-text-soft);font-variant-numeric:tabular-nums;text-decoration:line-through;opacity:.7}.summary-row .after{font-variant-numeric:tabular-nums;font-weight:500}.summary .note-line{margin:10px 0;font-size:12.5px;color:var(--myhome-text-soft)}.code{background:var(--myhome-background-soft);border-radius:8px;padding:12px 14px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-x:auto}.stub{margin:4px 0 0;background:var(--myhome-info-pastel);border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.55}`;var Ji=/^\/myhome_static\/[A-Za-z0-9._~\-/]+$/,en=/(^|\/)\.\.?(\/|$)/,xi=/^[A-Za-z0-9 %.,\-]+$/,tn=n=>{if(!Ji.test(n.src)||en.test(n.src))return null;let i=n.size&&xi.test(n.size)?n.size:"100% auto",e=n.pos&&xi.test(n.pos)?n.pos:"50% 60%";return{backgroundImage:`url("${n.src}")`,backgroundSize:i,backgroundPosition:e}},Le=class extends g{constructor(){super();this._fire=(e,t)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:e,value:t,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new b}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[k,R,E,z,ye,yi,u`:host{display:block;background:transparent}.screen{width:100%;max-width:480px;margin:0 auto;display:flex;flex-direction:column;position:relative}main{flex:1;padding:16px 16px 230px}.right{min-width:0}.footer{position:fixed;bottom:0;left:50%;transform:translate(-50%);width:100%;max-width:480px;padding:36px 16px calc(12px + env(safe-area-inset-bottom,0px));background:linear-gradient(to top,var(--myhome-background) calc(100% - 36px),transparent);z-index:25;display:flex;flex-direction:column;gap:10px}@media(min-width:900px){.screen{max-width:100%}main{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:0 44px;align-items:start;width:100%;max-width:1080px;margin:0 auto;padding:24px 32px 48px}main.single{display:block;max-width:560px}.right{position:sticky;top:76px}.footer{position:static;transform:none;width:auto;max-width:none;padding:0;background:none;margin-top:20px}}`]}_renderOperative(e,t){switch(e.model){case"scelta":return mi(e,t);case"pos":return vi(e,t);case"click":return gi(e,t);case"controllo":return fi(e,t);case"metro":return _i(e,t);case"riepilogo":return wi(e,t);case"esito":return bi(e,t);case"lettura":return ui(e,t);default:return l}}_renderFooter(e,t){let r=e.secondary??[];return!e.primary&&r.length===0?l:a`<div class="footer">
      ${e.primary?a`<button
            class="big ${e.press?.state==="moving"?"moving":""}"
            type="button"
            ?disabled=${e.primary.disabled}
            @click=${()=>this._fire(e.primary.action)}
          >
            ${e.primary.label}
          </button>`:l}
      ${r.map(o=>a`<button
          class="cta ${o.kind==="text"?"text":"secondary"}"
          type="button"
          ?disabled=${o.disabled}
          @click=${()=>t.fire(o.action)}
        >
          ${o.label}
        </button>`)}
    </div>`}render(){let e=this.model;if(!e)return l;let t={i18n:this.i18n,fire:this._fire},r=e.model==="pos",o=e.image?tn(e.image):null;return a`<div class="screen">
      <main class=${r?"single":""}>
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
                style=${hi(o)}
              ></div>`:l}
          ${e.body?a`<div class="prose">${B(e.body)}</div>`:l}
        </div>
        <div class="right">
          ${this._renderOperative(e,t)} ${this._renderFooter(e,t)}
        </div>
      </main>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",Le);var nn=3e4,rn=7e3,tt=400,on=2e3,it=class extends g{constructor(){super();this._i18n=new b;this._router=new _e;this._store=new we(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._snackTimer=null;this._previewTimer=null;this._travelTimer=null;this._impactTimer=null;this._followTimer=null;this._followedAt=0;this._previewSeq=0;this._onReturn=()=>{!this._started||document.hidden||this._refresh()};this._assignActions={search:e=>this._store.set({search:e}),room:e=>this._store.set({room:e}),clearFilters:()=>this._store.set({search:"",room:""}),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:(e,t)=>{if(this._locked)return;let{pending:r,withdrawn:o}=Dt(this._store.state.pending,e,t);this._store.set({pending:r,dialog:null,armed:null,writeError:null}),this._store.announce(o?this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name}):this._i18n.t("panel.assign.announce.pending",{cover:e.name,target:t===null?this._i18n.t("panel.assign.target_none"):this._i18n.t("panel.assign.target_profile",{profile:t})})),this._schedulePreview()},withdraw:e=>{this._store.set({pending:this._store.state.pending.filter(t=>t.cover!==e.unique_id)}),this._store.announce(this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name})),this._schedulePreview()},discardAll:()=>{this._store.set({...be}),this._store.announce(this._i18n.t("panel.assign.announce.discarded"))},reorder:e=>{this._locked||!this._store.state.entryId||(this._store.set({order:e}),this._write(()=>Pt(this.hass.connection,this._store.state.entryId,e),t=>{this._store.set({order:null}),this._store.setOverview(t.overview),this._snack(this._i18n.t("panel.toast.order_saved"),t.undo_token),this._store.announce(this._i18n.t("panel.assign.announce.reordered"))},t=>{this._store.set({order:null,writeError:null}),this._snack(t,null,!1)}))},setOrder:e=>this._store.set({order:e}),drag:e=>this._store.set({drag:e?{cover:e.unique_id,name:e.name,over:null,insert:null}:null}),over:e=>{let t=this._store.state.drag;t&&this._store.set({drag:{...t,over:e?.group??null,insert:e?{...e}:null}})},arm:e=>{this._store.set({armed:e?e.unique_id:null}),e&&this._store.announce(this._i18n.t("panel.assign.announce.armed"))},dialog:e=>this._store.set({dialog:e?e.unique_id:null}),review:e=>{this._store.set({review:e,writeError:null,heightsForced:!1}),e&&this._refreshPreview()},height:(e,t)=>{this._store.set({heights:{...this._store.state.heights,[e]:t}}),this._schedulePreview()},toggleShowAll:()=>this._store.set({showAll:!this._store.state.showAll}),confirm:()=>{this._confirm()},undo:()=>{this._undo()},announce:e=>this._store.announce(e)};this._detailActions={back:()=>this._navigate("/"),retry:()=>{this._store.set({detail:{...this._store.state.detail,loading:!0,error:null}}),this._loadDetail()},openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:()=>{let e=this._store.state.detail.for;this._store.set({dialog:e}),this._navigate("/")},mode:e=>{let t=this._store.state.detail,r=this._detailCover,o=e==="edit"?this._detailForm():e==="travel"?{height:r?.height!=null?this._i18n.number(r.height,0):""}:{};this._store.set({detail:{...t,mode:e,form:o,errors:{},preview:null,previewing:!1},writeError:null}),e==="travel"&&this._refreshTravelPreview()},field:(e,t)=>{let r=this._store.state.detail,o=e==="height"&&w("height",t)!==null;o&&(this._previewSeq+=1),this._store.set({detail:{...r,form:{...r.form,[e]:t},...o?{preview:null}:{}}}),e==="height"&&this._scheduleTravelPreview()},saveValues:()=>{this._saveValues()},saveTravel:()=>{this._saveTravel()},remove:()=>{this._removeMeasure()},openFlow:e=>this._openFlow(e)};this._profileActions={back:()=>this._navigate("/"),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),mode:e=>{let t=this._store.state.profile;this._store.set({profile:{...t,mode:e,form:e==="edit"?this._profileForm(this._profileRow):{},errors:{},newName:e==="rename"?t.for??"":"",nameError:"",impact:null,impacting:!1},writeError:null}),e==="edit"&&this._refreshImpact()},field:(e,t)=>{let r=this._store.state.profile;this._store.set({profile:{...r,form:{...r.form,[e]:t}}}),this._scheduleImpact()},newName:e=>this._store.set({profile:{...this._store.state.profile,newName:e,nameError:""}}),saveValues:()=>{this._saveProfile()},rename:()=>{this._renameProfile()},remove:()=>{this._deleteProfile()}};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[k,R,E,ye,jt,$e,u`.toolbar{display:flex;align-items:center;gap:8px;padding:0 8px;background:var(--myhome-header);color:var(--myhome-header-text);font-size:20px;font-weight:400;padding-top:env(safe-area-inset-top,0px);height:calc(56px + env(safe-area-inset-top,0px))}.toolbar .title{flex:1;min-width:0;margin:0;font-size:inherit;font-weight:inherit;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar select.gateway{font:inherit;font-size:13px;max-width:40%;min-height:44px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;padding:0 6px}.toolbar select.gateway option{color:var(--myhome-text);background:var(--myhome-card)}.toolbar button{width:48px;height:48px;flex:0 0 48px;border:0;border-radius:24px;background:transparent;color:inherit;font-size:20px;line-height:1;cursor:pointer}.content{padding:16px;max-width:1200px;margin:0 auto;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}.card.problem{background:var(--myhome-error-pastel);color:var(--myhome-text);padding:16px}.card.waiting{color:var(--myhome-text-soft);padding:16px}.soft{color:var(--myhome-text-soft);font-size:13px;margin-top:8px}.connection{margin:24px 0 0;font-size:12.5px;color:var(--myhome-text-soft)}a{color:var(--myhome-primary)}`]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(e=>this._onRoute(e)),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._stopPolling(),this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._previewTimer&&(clearTimeout(this._previewTimer),this._previewTimer=null),this._travelTimer&&(clearTimeout(this._travelTimer),this._travelTimer=null),this._impactTimer&&(clearTimeout(this._impactTimer),this._impactTimer=null),this._followTimer&&(clearTimeout(this._followTimer),this._followTimer=null);let e=this._unsubscribeWs;this._unsubscribeWs=null,e?.().catch(()=>{})}shouldUpdate(e){return e.size>1||!e.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(e){if(e.has("route")&&(this._router.setHostPath(this.route?.path),this._onRoute(this._router.current)),!(!e.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_languageOf(e){return e?.locale?.language||e?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,await this._loadTexts(),await this._refresh(),await this._loadDetail(),await this._listen())}async _loadTexts(){let e=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,e)}catch{}this._language=e,this.requestUpdate()}async _refresh(){try{let e=await xt(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(e)}catch(e){this._store.setError(C(e))}}async _listen(){let e=this._unsubscribeWs;this._unsubscribeWs=null,await e?.().catch(()=>{});try{this._unsubscribeWs=await Rt(this.hass.connection,this._store.state.entryId,t=>this._onEvent(t)),this._store.set({connection:"live"}),this._stopPolling()}catch(t){ee(t)||console.warn("MyHOME panel: live updates are not available",C(t)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(e){if(e.type==="overview"){this._store.setOverview(e.overview),this._followPush();return}if(e.type==="measuring"){let t=this._store.state.overview;if(!t)return;this._store.set({overview:{...t,measuring:e.cover_unique_id?{cover_unique_id:e.cover_unique_id,name:e.name??""}:null}}),e.cover_unique_id&&(this._store.set({armed:null,drag:null}),this._store.announce(this._i18n.t("panel.banner.measuring.body",{cover:e.name??""})))}}_followPush(){if(this._followTimer)return;let e=Math.max(0,on-(Date.now()-this._followedAt));this._followTimer=setTimeout(()=>{this._followTimer=null,this._followedAt=Date.now(),this._store.state.review&&this._schedulePreview(),this._store.state.detail.for&&this._loadDetail()},e)}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},nn))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}_onRoute(e){if(this._store.set({route:e}),e.view==="cover"){let t=e.params.id;this._store.state.detail.for!==t&&(this._store.set({detail:{...ne,for:t,loading:!0}}),this._loadDetail())}else this._store.state.detail.for!==null&&this._store.set({detail:ne});if(e.view==="profile"){let t=e.params.name;this._store.state.profile.for!==t&&this._store.set({profile:{...re,for:t}})}else this._store.state.profile.for!==null&&this._store.set({profile:re});this._started&&this._store.set({writeError:null})}get _version(){return this.panel?.config?.version??""}_navigate(e){this._router.navigate(e)}_renderMenuButton(){return this.narrow?Ot("ha-menu-button")?a`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:a`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>zt(this)}
    >
      ☰
    </button>`:l}_renderBackButton(){return this._store.state.route.view==="overview"?l:a`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.back")}
      @click=${()=>this._navigate("/")}
    >
      ←
    </button>`}_renderPlaceholder(e,t){let r={id:"panel.common.not_yet",model:"lettura",title:e,body:t,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return a`<myhome-screen
      .model=${r}
      .i18n=${this._i18n}
      @myhome-screen-action=${o=>{o.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}get _locked(){let e=this._store.state;return e.overview?.measuring!=null||e.applying}async _confirm(){let e=this._store.state,t=e.entryId;if(this._locked||!t||e.pending.length===0)return;if(e.pending.filter(p=>{let d=e.overview?.covers.find(c=>c.unique_id===p.cover);return d!==void 0&&qt(d,p)&&te(e.heights[p.cover])!==null}).length>0){this._store.set({heightsForced:!0}),this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));return}let o=Ze(e.pending,e.heights),s=e.order??void 0;this._store.announce(this._i18n.t("panel.assign.announce.applying")),await this._write(()=>Et(this.hass.connection,t,o,s),p=>{this._store.set({...be}),this._store.setOverview(p.overview),this._snack(p.applied===1?this._i18n.t("panel.toast.assigned_one"):this._i18n.t("panel.toast.assigned",{count:p.applied}),p.undo_token)})}async _undo(){let e=this._store.state,t=e.snack?.undoToken;if(!t||!e.entryId)return;let r=e.entryId;this._clearSnack(),await this._write(()=>Lt(this.hass.connection,r,t),o=>{this._store.setOverview(o.overview),this._snack(this._i18n.t("panel.toast.undone"),null)})}async _write(e,t,r){this._store.set({applying:!0,writeError:null});try{let o=await e();this._store.set({applying:!1}),t(o)}catch(o){let s=C(o);this._store.set({applying:!1,writeError:s});let p=this._i18n.refusal(s.translation_key,s.translation_placeholders??{});this._store.announce(p),r?.(p)}}_snack(e,t,r=!0){this._clearSnack(),this._store.set({snack:{message:e,undoToken:t}}),r&&this._store.announce(e),this._snackTimer=setTimeout(()=>{this._snackTimer=null,this._store.set({snack:null})},rn)}_clearSnack(){this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._store.set({snack:null})}_schedulePreview(){this._store.state.review&&(this._previewTimer&&clearTimeout(this._previewTimer),this._previewTimer=setTimeout(()=>{this._previewTimer=null,this._refreshPreview()},tt))}async _refreshPreview(){let e=this._store.state;if(!e.entryId||e.pending.length===0){this._store.set({preview:null});return}let t=++this._previewSeq;this._store.set({previewing:!0});try{let r=await ue(this.hass.connection,e.entryId,Ze(e.pending,e.heights));t===this._previewSeq&&this._store.set({preview:r.items,previewing:!1})}catch(r){t===this._previewSeq&&this._store.set({previewing:!1}),ee(r)||console.warn("MyHOME panel: the preview could not be read",C(r))}}get _detailCover(){let e=this._store.state,t=e.detail.for;return e.overview?.covers.find(r=>r.unique_id===t)??null}async _loadDetail(){let e=this._store.state,t=e.detail.for;if(!(!this._started||!this.hass||!t||!e.entryId))try{let r=await kt(this.hass.connection,e.entryId,t);if(this._store.state.detail.for!==t)return;this._store.set({detail:{...this._store.state.detail,answer:r,loading:!1,error:null}})}catch(r){if(this._store.state.detail.for!==t)return;this._store.set({detail:{...this._store.state.detail,answer:null,loading:!1,error:C(r)}})}}_detailForm(){let e=this._store.state.detail.answer,t={};for(let r of K){let o=e?.keys.find(s=>s.key===r);t[r]=o&&o.own?this._i18n.number(o.value,x[r]??1):""}return t}async _saveValues(){let e=this._store.state,t=e.detail.for;if(this._locked||!t||!e.entryId)return;let r={};for(let d of K){let c=e.detail.form[d];if(w(d,c)!==null)return;r[d]=$(c)?null:A(c??"")}let o=Object.values(r).every(d=>d===null),s=this._detailCover?.name??"",p=e.entryId;await this._write(()=>St(this.hass.connection,p,t,r),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{}}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(o?this._i18n.t("panel.toast.measure_removed",{cover:s,destination:this._destinationOf(d.overview,t)}):this._i18n.t("panel.toast.values_saved",{cover:s}),d.undo_token)})}async _saveTravel(){let e=this._store.state,t=e.detail.for,r=e.detail.form.height;if(this._locked||!t||!e.entryId||$(r)||w("height",r))return;let o=A(r??""),s=this._detailCover?.name??"",p=e.entryId;await this._write(()=>Tt(this.hass.connection,p,t,o),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{},preview:null}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.travel_saved",{cover:s}),d.undo_token)})}async _removeMeasure(){let e=this._store.state,t=e.detail.for;if(this._locked||!t||!e.entryId)return;let r=this._detailCover?.name??"",o=e.entryId;await this._write(()=>Ct(this.hass.connection,o,t),s=>{this._store.set({detail:{...this._store.state.detail,mode:"view"}}),this._store.setOverview(s.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.measure_removed",{cover:r,destination:s.falls_back_to==="profile"?this._i18n.t("panel.detail.destination.profile",{profile:s.profile??""}):s.falls_back_to==="file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}),s.undo_token)})}_destinationOf(e,t){let r=e.covers.find(o=>o.unique_id===t);return r?.origin==="inherited"||r?.origin==="adjusted"?this._i18n.t("panel.detail.destination.profile",{profile:r.profile??""}):r?.origin==="from_the_file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}_scheduleTravelPreview(){this._travelTimer&&clearTimeout(this._travelTimer),this._travelTimer=setTimeout(()=>{this._travelTimer=null,this._refreshTravelPreview()},tt)}async _refreshTravelPreview(){let e=this._store.state,t=this._detailCover,r=e.detail.form.height;if(!e.entryId||!t||$(r)||w("height",r)!==null){this._store.set({detail:{...this._store.state.detail,preview:null}});return}let o=++this._previewSeq;this._store.set({detail:{...this._store.state.detail,previewing:!0}});try{let s=await ue(this.hass.connection,e.entryId,[{...Qe(t),height:A(r??"")}]);if(o!==this._previewSeq)return;this._store.set({detail:{...this._store.state.detail,preview:s.items[0]??null,previewing:!1}})}catch(s){o===this._previewSeq&&this._store.set({detail:{...this._store.state.detail,previewing:!1}}),ee(s)||console.warn("MyHOME panel: the preview could not be read",C(s))}}_openFlow(e){Ut({source:e,entryId:this._store.state.entryId,onLeaving:()=>this._store.announce(this._i18n.t("panel.common.opens_configure"))})}_title(){let e=this._store.state,t=e.route;if(t.view==="cover"){let r=this._detailCover;return r?this._i18n.t("panel.detail.named",{cover:r.name}):this._i18n.t("panel.detail.title")}return t.view==="profile"?e.overview?.profiles.some(o=>o.name===t.params.name)?this._i18n.t("panel.profile.name",{profile:t.params.name}):this._i18n.t("panel.profile.title"):this._i18n.t("panel.overview.title")}get _profileRow(){let e=this._store.state;return e.overview?.profiles.find(t=>t.name===e.profile.for)??null}_followersOf(e){let t=this._store.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return t.filter(o=>r.has(o.unique_id))}_profileForm(e){let t={};for(let r of j){let o=r==="reference_height"?e?.reference_height:e?.values[r];t[r]=o==null?"":this._i18n.number(o,x[r]??0)}return t}_typedProfile(){let e=this._store.state.profile.form,t={};for(let r of j){if($(e[r])||w(r,e[r])!==null)return null;t[r]=A(e[r]??"")}return t}async _saveProfile(){let e=this._store.state,t=e.profile.for,r=this._typedProfile();if(this._locked||!t||!e.entryId||!r)return;let{reference_height:o,...s}=r,p=e.entryId;await this._write(()=>At(this.hass.connection,p,t,s,o),d=>{this._store.set({profile:{...this._store.state.profile,mode:"view",impact:null}}),this._store.setOverview(d.overview),this._snack(d.affected.length===1?this._i18n.t("panel.toast.profile_saved_one",{profile:t}):this._i18n.t("panel.toast.profile_saved",{profile:t,count:d.affected.length}),d.undo_token)})}async _renameProfile(){let e=this._store.state,t=e.profile.for,r=e.profile.newName.trim();if(this._locked||!t||!e.entryId||!r||r===t)return;let o=e.entryId;await this._write(()=>It(this.hass.connection,o,t,r),s=>{this._store.setOverview(s.overview),this._navigate(`/profile/${encodeURIComponent(r)}`),this._snack(this._i18n.t("panel.toast.profile_renamed",{profile:r}),s.undo_token)},s=>this._store.set({profile:{...this._store.state.profile,nameError:s},writeError:null}))}async _deleteProfile(){let e=this._store.state,t=e.profile.for;if(this._locked||!t||!e.entryId)return;let r=e.entryId;await this._write(()=>Mt(this.hass.connection,r,t),o=>{this._store.setOverview(o.overview),this._navigate("/"),this._snack(this._i18n.t("panel.toast.profile_deleted",{profile:t}),o.undo_token)})}_scheduleImpact(){this._impactTimer&&clearTimeout(this._impactTimer),this._impactTimer=setTimeout(()=>{this._impactTimer=null,this._refreshImpact()},tt)}async _refreshImpact(){let e=this._store.state,t=this._typedProfile(),r=e.profile.for,o=this._followersOf(this._profileRow);if(!e.entryId||!r||!t||o.length===0){this._store.set({profile:{...this._store.state.profile,impact:null}});return}let s=++this._previewSeq;this._store.set({profile:{...this._store.state.profile,impacting:!0}});try{let p=await ue(this.hass.connection,e.entryId,o.map(d=>Qe(d)),{[r]:t});if(s!==this._previewSeq)return;this._store.set({profile:{...this._store.state.profile,impact:p.items,impacting:!1}})}catch(p){s===this._previewSeq&&this._store.set({profile:{...this._store.state.profile,impacting:!1}}),ee(p)||console.warn("MyHOME panel: the impact preview could not be read",C(p))}}async _retry(){await this._refresh(),this._store.state.connection!=="live"&&await this._listen()}_renderView(){let e=this._store.state;if(e.status==="loading")return a`<div class="card waiting" role="status">
        ${this._i18n.t("panel.common.loading")}
      </div>`;if(e.status==="error"||!e.overview){let r=e.error;return a`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(r?.translation_key,r?.translation_placeholders??{})}
        </div>
        <div class="soft">${r?`${r.code}: ${r.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._retry()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${L}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?a` · ${this._version}`:l}
        </div>
      </div>`}let t=e.route;return t.view==="cover"?a`<myhome-cover-detail
        .i18n=${this._i18n}
        .state=${e}
        .actions=${this._detailActions}
      ></myhome-cover-detail>`:t.view==="profile"?a`<myhome-profile-card
        .i18n=${this._i18n}
        .state=${e}
        .actions=${this._profileActions}
      ></myhome-profile-card>`:t.view!=="overview"?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):a`<myhome-overview
      .i18n=${this._i18n}
      .state=${e}
      .actions=${this._assignActions}
    ></myhome-overview>`}render(){let e=this._store.state,t=this._title(),r=e.overview?.measuring??null,o=e.route.view!=="overview";return a`
      <div class="toolbar">
        ${this._renderMenuButton()} ${this._renderBackButton()}
        <h1 class="title">${t}</h1>
        ${this._renderGatewayPicker()}
      </div>
      ${r?Gt(this._i18n,r.name,L):l}
      <div class="content">
        ${Kt(e.announce)} ${this._renderView()}
        ${e.connection==="polling"&&e.status==="ready"?a`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:l}
      </div>
      <!--
        The overview draws its own five strips, because three of them are about a gesture
        it owns. The routed cards have no gestures and two of the five still apply to them:
        a write in the air, and what it came to with "Annulla" beside it.
      -->
      ${o&&e.applying?ke(this._i18n):l}
      ${o&&e.snack&&!e.applying?Re(this._i18n,e.snack.message,e.snack.undoToken?()=>{this._undo()}:null):l}
    `}_renderGatewayPicker(){let e=this._store.state,t=e.overview?.entries??[],r=t.find(s=>s.entry_id===e.entryId);if(t.length<=1)return l;let o=this._i18n.t("panel.common.gateway",{gateway:r?.title??""});return a`<select
      class="gateway"
      aria-label=${o}
      .value=${e.entryId??""}
      ?disabled=${e.applying}
      @change=${s=>{this._switchGateway(s.target.value)}}
    >
      ${t.map(s=>a`<option value=${s.entry_id} ?selected=${s.entry_id===e.entryId}>
          ${s.title}
        </option>`)}
    </select>`}async _switchGateway(e){if(!e||e===this._store.state.entryId)return;let t=this._unsubscribeWs;this._unsubscribeWs=null,await t?.().catch(()=>{}),this._clearSnack(),this._store.set({...be,entryId:e,detail:ne,profile:re,search:"",room:"",snack:null}),this._navigate("/"),await this._refresh(),await this._listen()}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",it);export{it as MyHomeCalibrationPanel};
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
