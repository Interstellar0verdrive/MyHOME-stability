/* MyHOME calibration panel */
var Ee=globalThis,Te=Ee.ShadowRoot&&(Ee.ShadyCSS===void 0||Ee.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,pt=Symbol(),ti=new WeakMap,ae=class{constructor(i,e,t){if(this._$cssResult$=!0,t!==pt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=i,this.t=e}get styleSheet(){let i=this.o,e=this.t;if(Te&&i===void 0){let t=e!==void 0&&e.length===1;t&&(i=ti.get(e)),i===void 0&&((this.o=i=new CSSStyleSheet).replaceSync(this.cssText),t&&ti.set(e,i))}return i}toString(){return this.cssText}},ii=n=>new ae(typeof n=="string"?n:n+"",void 0,pt),m=(n,...i)=>{let e=n.length===1?n[0]:i.reduce((t,r,o)=>t+(s=>{if(s._$cssResult$===!0)return s.cssText;if(typeof s=="number")return s;throw Error("Value passed to 'css' function must be a 'css' function result: "+s+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+n[o+1],n[0]);return new ae(e,n,pt)},ni=(n,i)=>{if(Te)n.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of i){let t=document.createElement("style"),r=Ee.litNonce;r!==void 0&&t.setAttribute("nonce",r),t.textContent=e.cssText,n.appendChild(t)}},ht=Te?n=>n:n=>n instanceof CSSStyleSheet?(i=>{let e="";for(let t of i.cssRules)e+=t.cssText;return ii(e)})(n):n;var{is:hr,defineProperty:ur,getOwnPropertyDescriptor:mr,getOwnPropertyNames:vr,getOwnPropertySymbols:fr,getPrototypeOf:gr}=Object,Ce=globalThis,ri=Ce.trustedTypes,_r=ri?ri.emptyScript:"",wr=Ce.reactiveElementPolyfillSupport,le=(n,i)=>n,ut={toAttribute(n,i){switch(i){case Boolean:n=n?_r:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,i){let e=n;switch(i){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},si=(n,i)=>!hr(n,i),oi={attribute:!0,type:String,converter:ut,reflect:!1,useDefault:!1,hasChanged:si};Symbol.metadata??=Symbol("metadata"),Ce.litPropertyMetadata??=new WeakMap;var P=class extends HTMLElement{static addInitializer(i){this._$Ei(),(this.l??=[]).push(i)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(i,e=oi){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(i)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(i,e),!e.noAccessor){let t=Symbol(),r=this.getPropertyDescriptor(i,t,e);r!==void 0&&ur(this.prototype,i,r)}}static getPropertyDescriptor(i,e,t){let{get:r,set:o}=mr(this.prototype,i)??{get(){return this[e]},set(s){this[e]=s}};return{get:r,set(s){let l=r?.call(this);o?.call(this,s),this.requestUpdate(i,l,t)},configurable:!0,enumerable:!0}}static getPropertyOptions(i){return this.elementProperties.get(i)??oi}static _$Ei(){if(this.hasOwnProperty(le("elementProperties")))return;let i=gr(this);i.finalize(),i.l!==void 0&&(this.l=[...i.l]),this.elementProperties=new Map(i.elementProperties)}static finalize(){if(this.hasOwnProperty(le("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(le("properties"))){let e=this.properties,t=[...vr(e),...fr(e)];for(let r of t)this.createProperty(r,e[r])}let i=this[Symbol.metadata];if(i!==null){let e=litPropertyMetadata.get(i);if(e!==void 0)for(let[t,r]of e)this.elementProperties.set(t,r)}this._$Eh=new Map;for(let[e,t]of this.elementProperties){let r=this._$Eu(e,t);r!==void 0&&this._$Eh.set(r,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(i){let e=[];if(Array.isArray(i)){let t=new Set(i.flat(1/0).reverse());for(let r of t)e.unshift(ht(r))}else i!==void 0&&e.push(ht(i));return e}static _$Eu(i,e){let t=e.attribute;return t===!1?void 0:typeof t=="string"?t:typeof i=="string"?i.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(i=>this.enableUpdating=i),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(i=>i(this))}addController(i){(this._$EO??=new Set).add(i),this.renderRoot!==void 0&&this.isConnected&&i.hostConnected?.()}removeController(i){this._$EO?.delete(i)}_$E_(){let i=new Map,e=this.constructor.elementProperties;for(let t of e.keys())this.hasOwnProperty(t)&&(i.set(t,this[t]),delete this[t]);i.size>0&&(this._$Ep=i)}createRenderRoot(){let i=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ni(i,this.constructor.elementStyles),i}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(i=>i.hostConnected?.())}enableUpdating(i){}disconnectedCallback(){this._$EO?.forEach(i=>i.hostDisconnected?.())}attributeChangedCallback(i,e,t){this._$AK(i,t)}_$ET(i,e){let t=this.constructor.elementProperties.get(i),r=this.constructor._$Eu(i,t);if(r!==void 0&&t.reflect===!0){let o=(t.converter?.toAttribute!==void 0?t.converter:ut).toAttribute(e,t.type);this._$Em=i,o==null?this.removeAttribute(r):this.setAttribute(r,o),this._$Em=null}}_$AK(i,e){let t=this.constructor,r=t._$Eh.get(i);if(r!==void 0&&this._$Em!==r){let o=t.getPropertyOptions(r),s=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:ut;this._$Em=r;let l=s.fromAttribute(e,o.type);this[r]=l??this._$Ej?.get(r)??l,this._$Em=null}}requestUpdate(i,e,t,r=!1,o){if(i!==void 0){let s=this.constructor;if(r===!1&&(o=this[i]),t??=s.getPropertyOptions(i),!((t.hasChanged??si)(o,e)||t.useDefault&&t.reflect&&o===this._$Ej?.get(i)&&!this.hasAttribute(s._$Eu(i,t))))return;this.C(i,e,t)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(i,e,{useDefault:t,reflect:r,wrapped:o},s){t&&!(this._$Ej??=new Map).has(i)&&(this._$Ej.set(i,s??e??this[i]),o!==!0||s!==void 0)||(this._$AL.has(i)||(this.hasUpdated||t||(e=void 0),this._$AL.set(i,e)),r===!0&&this._$Em!==i&&(this._$Eq??=new Set).add(i))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let i=this.scheduleUpdate();return i!=null&&await i,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[r,o]of this._$Ep)this[r]=o;this._$Ep=void 0}let t=this.constructor.elementProperties;if(t.size>0)for(let[r,o]of t){let{wrapped:s}=o,l=this[r];s!==!0||this._$AL.has(r)||l===void 0||this.C(r,void 0,o,l)}}let i=!1,e=this._$AL;try{i=this.shouldUpdate(e),i?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(t){throw i=!1,this._$EM(),t}i&&this._$AE(e)}willUpdate(i){}_$AE(i){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(i)),this.updated(i)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(i){return!0}update(i){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(i){}firstUpdated(i){}};P.elementStyles=[],P.shadowRootOptions={mode:"open"},P[le("elementProperties")]=new Map,P[le("finalized")]=new Map,wr?.({ReactiveElement:P}),(Ce.reactiveElementVersions??=[]).push("2.1.2");var yt=globalThis,ai=n=>n,Ae=yt.trustedTypes,li=Ae?Ae.createPolicy("lit-html",{createHTML:n=>n}):void 0,mi="$lit$",H=`lit$${Math.random().toFixed(9).slice(2)}$`,vi="?"+H,yr=`<${vi}>`,G=document,ce=()=>G.createComment(""),pe=n=>n===null||typeof n!="object"&&typeof n!="function",bt=Array.isArray,br=n=>bt(n)||typeof n?.[Symbol.iterator]=="function",mt=`[ 	
\f\r]`,de=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,di=/-->/g,ci=/>/g,U=RegExp(`>|${mt}(?:([^\\s"'>=/]+)(${mt}*=${mt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),pi=/'/g,hi=/"/g,fi=/^(?:script|style|textarea|title)$/i,xt=n=>(i,...e)=>({_$litType$:n,strings:i,values:e}),a=xt(1),Eo=xt(2),To=xt(3),z=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),ui=new WeakMap,K=G.createTreeWalker(G,129);function gi(n,i){if(!bt(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return li!==void 0?li.createHTML(i):i}var xr=(n,i)=>{let e=n.length-1,t=[],r,o=i===2?"<svg>":i===3?"<math>":"",s=de;for(let l=0;l<e;l++){let c=n[l],p,u,h=-1,v=0;for(;v<c.length&&(s.lastIndex=v,u=s.exec(c),u!==null);)v=s.lastIndex,s===de?u[1]==="!--"?s=di:u[1]!==void 0?s=ci:u[2]!==void 0?(fi.test(u[2])&&(r=RegExp("</"+u[2],"g")),s=U):u[3]!==void 0&&(s=U):s===U?u[0]===">"?(s=r??de,h=-1):u[1]===void 0?h=-2:(h=s.lastIndex-u[2].length,p=u[1],s=u[3]===void 0?U:u[3]==='"'?hi:pi):s===hi||s===pi?s=U:s===di||s===ci?s=de:(s=U,r=void 0);let _=s===U&&n[l+1].startsWith("/>")?" ":"";o+=s===de?c+yr:h>=0?(t.push(p),c.slice(0,h)+mi+c.slice(h)+H+_):c+H+(h===-2?l:_)}return[gi(n,o+(n[e]||"<?>")+(i===2?"</svg>":i===3?"</math>":"")),t]},he=class n{constructor({strings:i,_$litType$:e},t){let r;this.parts=[];let o=0,s=0,l=i.length-1,c=this.parts,[p,u]=xr(i,e);if(this.el=n.createElement(p,t),K.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(r=K.nextNode())!==null&&c.length<l;){if(r.nodeType===1){if(r.hasAttributes())for(let h of r.getAttributeNames())if(h.endsWith(mi)){let v=u[s++],_=r.getAttribute(h).split(H),E=/([.?@])?(.*)/.exec(v);c.push({type:1,index:o,name:E[2],strings:_,ctor:E[1]==="."?ft:E[1]==="?"?gt:E[1]==="@"?_t:Q}),r.removeAttribute(h)}else h.startsWith(H)&&(c.push({type:6,index:o}),r.removeAttribute(h));if(fi.test(r.tagName)){let h=r.textContent.split(H),v=h.length-1;if(v>0){r.textContent=Ae?Ae.emptyScript:"";for(let _=0;_<v;_++)r.append(h[_],ce()),K.nextNode(),c.push({type:2,index:++o});r.append(h[v],ce())}}}else if(r.nodeType===8)if(r.data===vi)c.push({type:2,index:o});else{let h=-1;for(;(h=r.data.indexOf(H,h+1))!==-1;)c.push({type:7,index:o}),h+=H.length-1}o++}}static createElement(i,e){let t=G.createElement("template");return t.innerHTML=i,t}};function Z(n,i,e=n,t){if(i===z)return i;let r=t!==void 0?e._$Co?.[t]:e._$Cl,o=pe(i)?void 0:i._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),o===void 0?r=void 0:(r=new o(n),r._$AT(n,e,t)),t!==void 0?(e._$Co??=[])[t]=r:e._$Cl=r),r!==void 0&&(i=Z(n,r._$AS(n,i.values),r,t)),i}var vt=class{constructor(i,e){this._$AV=[],this._$AN=void 0,this._$AD=i,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(i){let{el:{content:e},parts:t}=this._$AD,r=(i?.creationScope??G).importNode(e,!0);K.currentNode=r;let o=K.nextNode(),s=0,l=0,c=t[0];for(;c!==void 0;){if(s===c.index){let p;c.type===2?p=new ue(o,o.nextSibling,this,i):c.type===1?p=new c.ctor(o,c.name,c.strings,this,i):c.type===6&&(p=new wt(o,this,i)),this._$AV.push(p),c=t[++l]}s!==c?.index&&(o=K.nextNode(),s++)}return K.currentNode=G,r}p(i){let e=0;for(let t of this._$AV)t!==void 0&&(t.strings!==void 0?(t._$AI(i,t,e),e+=t.strings.length-2):t._$AI(i[e])),e++}},ue=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(i,e,t,r){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=i,this._$AB=e,this._$AM=t,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let i=this._$AA.parentNode,e=this._$AM;return e!==void 0&&i?.nodeType===11&&(i=e.parentNode),i}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(i,e=this){i=Z(this,i,e),pe(i)?i===d||i==null||i===""?(this._$AH!==d&&this._$AR(),this._$AH=d):i!==this._$AH&&i!==z&&this._(i):i._$litType$!==void 0?this.$(i):i.nodeType!==void 0?this.T(i):br(i)?this.k(i):this._(i)}O(i){return this._$AA.parentNode.insertBefore(i,this._$AB)}T(i){this._$AH!==i&&(this._$AR(),this._$AH=this.O(i))}_(i){this._$AH!==d&&pe(this._$AH)?this._$AA.nextSibling.data=i:this.T(G.createTextNode(i)),this._$AH=i}$(i){let{values:e,_$litType$:t}=i,r=typeof t=="number"?this._$AC(i):(t.el===void 0&&(t.el=he.createElement(gi(t.h,t.h[0]),this.options)),t);if(this._$AH?._$AD===r)this._$AH.p(e);else{let o=new vt(r,this),s=o.u(this.options);o.p(e),this.T(s),this._$AH=o}}_$AC(i){let e=ui.get(i.strings);return e===void 0&&ui.set(i.strings,e=new he(i)),e}k(i){bt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,t,r=0;for(let o of i)r===e.length?e.push(t=new n(this.O(ce()),this.O(ce()),this,this.options)):t=e[r],t._$AI(o),r++;r<e.length&&(this._$AR(t&&t._$AB.nextSibling,r),e.length=r)}_$AR(i=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);i!==this._$AB;){let t=ai(i).nextSibling;ai(i).remove(),i=t}}setConnected(i){this._$AM===void 0&&(this._$Cv=i,this._$AP?.(i))}},Q=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(i,e,t,r,o){this.type=1,this._$AH=d,this._$AN=void 0,this.element=i,this.name=e,this._$AM=r,this.options=o,t.length>2||t[0]!==""||t[1]!==""?(this._$AH=Array(t.length-1).fill(new String),this.strings=t):this._$AH=d}_$AI(i,e=this,t,r){let o=this.strings,s=!1;if(o===void 0)i=Z(this,i,e,0),s=!pe(i)||i!==this._$AH&&i!==z,s&&(this._$AH=i);else{let l=i,c,p;for(i=o[0],c=0;c<o.length-1;c++)p=Z(this,l[t+c],e,c),p===z&&(p=this._$AH[c]),s||=!pe(p)||p!==this._$AH[c],p===d?i=d:i!==d&&(i+=(p??"")+o[c+1]),this._$AH[c]=p}s&&!r&&this.j(i)}j(i){i===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,i??"")}},ft=class extends Q{constructor(){super(...arguments),this.type=3}j(i){this.element[this.name]=i===d?void 0:i}},gt=class extends Q{constructor(){super(...arguments),this.type=4}j(i){this.element.toggleAttribute(this.name,!!i&&i!==d)}},_t=class extends Q{constructor(i,e,t,r,o){super(i,e,t,r,o),this.type=5}_$AI(i,e=this){if((i=Z(this,i,e,0)??d)===z)return;let t=this._$AH,r=i===d&&t!==d||i.capture!==t.capture||i.once!==t.once||i.passive!==t.passive,o=i!==d&&(t===d||r);r&&this.element.removeEventListener(this.name,this,t),o&&this.element.addEventListener(this.name,this,i),this._$AH=i}handleEvent(i){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,i):this._$AH.handleEvent(i)}},wt=class{constructor(i,e,t){this.element=i,this.type=6,this._$AN=void 0,this._$AM=e,this.options=t}get _$AU(){return this._$AM._$AU}_$AI(i){Z(this,i)}};var $r=yt.litHtmlPolyfillSupport;$r?.(he,ue),(yt.litHtmlVersions??=[]).push("3.3.3");var _i=(n,i,e)=>{let t=e?.renderBefore??i,r=t._$litPart$;if(r===void 0){let o=e?.renderBefore??null;t._$litPart$=r=new ue(i.insertBefore(ce(),o),o,void 0,e??{})}return r._$AI(n),r};var $t=globalThis,w=class extends P{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let i=super.createRenderRoot();return this.renderOptions.renderBefore??=i.firstChild,i}update(i){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(i),this._$Do=_i(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return z}};w._$litElement$=!0,w.finalized=!0,$t.litElementHydrateSupport?.({LitElement:w});var kr=$t.litElementPolyfillSupport;kr?.({LitElement:w});($t.litElementVersions??=[]).push("4.2.2");var wi={"panel.assign.action.discard_all":"Discard everything","panel.assign.action.review":"Review and confirm","panel.assign.action.review_hint":"Review and confirm the assignments","panel.assign.action.withdraw":"Withdraw this change","panel.assign.announce.applying":"The changes are being applied.","panel.assign.announce.armed":"Tap the destination group.","panel.assign.announce.discarded":"Every pending change has been discarded.","panel.assign.announce.drag_cancelled":"Drag cancelled.","panel.assign.announce.missing_travel":"Some covers have no travel.","panel.assign.announce.pending":"«{cover}» is pending, towards {target}. Nothing is written yet.","panel.assign.announce.reordered":"Order updated: it will be remembered.","panel.assign.announce.withdrawn":"«{cover}» goes back where it was: the change is withdrawn.","panel.assign.armed":"Tap the destination group for «{cover}»","panel.assign.drop_zone":"Take out of the profile — drop here","panel.assign.handle":"Move {cover} to another group, or reorder it","panel.assign.handle_hint":"Drag to assign or reorder, Enter to pick from a list","panel.assign.pending.all_own":"All values its own: nothing changes","panel.assign.pending.count":"{count} pending changes — nothing is written yet","panel.assign.pending.count_one":"1 pending change — nothing is written yet","panel.assign.pending.route":"{from} → {to}","panel.assign.pending.route_name":"«{profile}»","panel.assign.pending.some_own":"Own values: those stay","panel.assign.target_none":"«No profile»","panel.assign.target_profile":"the profile «{profile}»","panel.banner.applying.body":"The covers are unavailable for a few seconds","panel.banner.applying.title":"The changes are being applied…","panel.banner.measuring.action.resume":"Resume the session","panel.banner.measuring.action.stop":"End it","panel.banner.measuring.body":"A guided calibration is using «{cover}». Until the session ends, this panel only reads: nothing is written.","panel.banner.measuring.end_panel_confirm":"End the guided calibration of «{cover}»? The measurements taken so far are discarded, and a run under way finishes by itself at its end stop.","panel.banner.measuring.panel_body":"A guided calibration of «{cover}» is running in this panel. Until it ends, this panel only reads: nothing is written.","panel.banner.measuring.title":"Measurement in progress","panel.common.action.back":"Back","panel.common.action.cancel":"Cancel","panel.common.action.close":"Close","panel.common.action.configure":"Open Configure","panel.common.action.hide_all":"Hide the roll coefficients","panel.common.action.menu":"Open the Home Assistant menu","panel.common.action.retry":"Try again","panel.common.action.save":"Save","panel.common.action.show_all":"Show every value, roll coefficients included","panel.common.advanced.body":"Slat opening time and roll coefficients are parameters of the position model and should only be changed with a precise understanding of what they mean and how they affect the position. When in doubt, obtaining them from the guided calibration is strongly recommended: it measures them on the real cover.","panel.common.advanced.title":"Advanced parameters","panel.common.all_rooms":"All rooms","panel.common.gateway":"Gateway {gateway}","panel.common.loading":"Loading…","panel.common.not_yet":"This screen arrives in a later version. Until then «Configure» does everything it will do.","panel.common.opens_configure":"This opens the Configure dialog. The panel refreshes on its own when it closes.","panel.common.polling":"Live updates are not available on this version: the page refreshes on its own every 30 seconds.","panel.common.reconnected":"Home Assistant is answering again: this page has just been read afresh.","panel.common.required":"This field cannot be left empty.","panel.common.room_filter":"Filter by room","panel.common.search":"Search for a cover","panel.common.unit.centimetres":"cm","panel.common.unit.seconds":"s","panel.detail.action.assign":"Assign to a profile…","panel.detail.action.correct":"Correct…","panel.detail.action.correct_note":"If it stops in the wrong place: times only, times and rolls, or the thorough calibration only","panel.detail.action.edit":"Edit the values by hand","panel.detail.action.measure_again":"Measure again","panel.detail.action.measure_again_note":"The guided calibration from the start: the route is chosen on the first screen","panel.detail.action.remove":"Remove the measurement…","panel.detail.action.thorough":"Thorough calibration","panel.detail.action.thorough_note":"On top: readings at 25 and 75 % per direction, and a check","panel.detail.action.travel":"Set the curtain travel…","panel.detail.correct.intro":"The correction runs in this panel, on the scope chosen here: only what it measures is written again, and nothing else of this shutter changes.","panel.detail.correct.thorough":"Thorough calibration only","panel.detail.correct.thorough_note":"Readings at 25 and 75 % per direction, and a check","panel.detail.correct.times":"Times only","panel.detail.correct.times_note":"One run per direction, the rolls stay","panel.detail.correct.times_rolls":"Times and rolls","panel.detail.correct.times_rolls_note":"Full basic calibration","panel.detail.destination.defaults":"the default values","panel.detail.destination.file":"the values of the configuration file","panel.detail.destination.profile":"the values inherited from the profile «{profile}»","panel.detail.edit.action.save":"Save the values","panel.detail.edit.empty":"empty = nothing to say","panel.detail.edit.inherits":"inherits {value}","panel.detail.edit.intro":"These values count for this cover alone and beat both the profile and the file. A field left empty is not a zero: it means «nothing to say about this one», and the value goes back to coming from the profile or from the file. Emptying every field is the same as removing the measurement.","panel.detail.edit.title":"Edit the values by hand","panel.detail.level_basic":"basic calibration","panel.detail.level_thorough":"thorough calibration","panel.detail.measured_at":"Measured on {date}","panel.detail.remove.action":"Remove the measurement","panel.detail.remove.body":"The measurements made on «{cover}» will be removed and cannot be recovered. The cover will go back to using {destination}.","panel.detail.remove.title":"Remove the measurement?","panel.detail.remove.travel_stays":"The curtain travel stays: somebody measured it with a tape.","panel.detail.source.default":"default value","panel.detail.source.file":"from the configuration file","panel.detail.source.own":"own value, measured on this cover","panel.detail.source.profile":"inherited from the profile «{profile}»","panel.detail.title":"Cover detail","panel.detail.unknown":"This gateway has no cover with that identifier.","panel.detail.values.intro":"What the cover is using right now, value by value, with where it comes from: a value of its own always wins; then the assigned profile, then the file, then the defaults.","panel.detail.values.title":"Values in use","panel.detail.verify_note":"{deviation} cm out at the check","panel.dialog.option.current":"current","panel.dialog.option.none":"No profile","panel.dialog.option.none_meta":"Values from the configuration file, or the defaults. The travel and the values of its own stay.","panel.dialog.option.profile":"Profile «{profile}»","panel.dialog.option.profile_meta":"{travel} cm · ascent {opening} s · descent {closing} s","panel.dialog.subtitle":"«{cover}» — the choice stays pending until it is confirmed.","panel.dialog.title":"Which profile?","panel.error.no_connection":"Home Assistant is not answering. The panel will try again.","panel.error.not_found":"The panel could not read this gateway.","panel.firstrun.action.measure":"Measure a cover","panel.firstrun.body":"A **profile** describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.firstrun.how":"A profile is not written, it is measured. Pick one representative cover and measure it once, with the guided calibration: about three minutes. Similar covers can then follow it.","panel.firstrun.note":"The guided calibration runs in this panel: about three minutes, and when it is done the profile appears here.","panel.firstrun.title":"No profile yet","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.cover.follows":"follows «{profile}»","panel.overview.cover.origin_adjusted":"Adjusted","panel.overview.cover.origin_inherited":"Inherited","panel.overview.cover.profile_missing":"The profile «{profile}» is no longer defined: this cover is running on its own configuration.","panel.overview.cover.travel":"travel {travel} cm","panel.overview.cover.travel_needed":"travel to be entered","panel.overview.cover.travel_unknown":"travel not recorded","panel.overview.explanation":"A **profile** describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.overview.group.count":"{count} covers","panel.overview.group.count_one":"1 cover","panel.overview.group.empty":"No cover in this group.","panel.overview.group.from_file":"Stated in the configuration file: this is changed there, not here.","panel.overview.group.measured_on":"Measured on {cover} · {date}","panel.overview.group.measured_on_gone":"Measured on a cover this gateway no longer has · {date}","panel.overview.group.missing":"This profile is not defined any more: the covers below have quietly fallen back to their own configuration.","panel.overview.group.no_profile":"No profile","panel.overview.group.no_profile_note":"Values from the configuration file, or the defaults. It is not a fault: a cover with measurements of its own sits perfectly well here.","panel.overview.group.open":"Open the profile card","panel.overview.group.profile":"Profile «{profile}»","panel.overview.group.provenance_missing":"Where it was measured is not recorded.","panel.overview.group.values":"Reference travel {travel} cm · ascent {opening} s · descent {closing} s · slats {slat} s","panel.overview.group.values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.no_basic_covers":"Every cover of this gateway reports its own position, so there is no travel model to calibrate and nothing for this panel to do.","panel.overview.no_basic_covers_title":"Nothing to calibrate on this gateway","panel.overview.no_results":"No cover matches this search.","panel.overview.summary":"Profiles: {profiles} · Basic covers: {covers}","panel.overview.title":"Profiles and covers","panel.profile.action.delete":"Delete the profile…","panel.profile.action.edit":"Edit the values…","panel.profile.action.rename":"Rename…","panel.profile.delete.action":"Delete the profile","panel.profile.delete.affects":"It affects these covers:","panel.profile.delete.body":"They will go back to the values of the configuration file, where those exist, or to the defaults. Their travels and their own values stay. The profile's measurements cannot be recovered.","panel.profile.delete.title":"Delete the profile «{profile}»?","panel.profile.edit.action.save":"Apply to {count} covers","panel.profile.edit.action.save_one":"Apply to 1 cover","panel.profile.edit.intro":"A change to the profile changes everything for the covers that inherit its values, and only the inherited values for the adjusted ones: the values of their own stay, key by key.","panel.profile.edit.reach":"The change reaches {target}","panel.profile.edit.reach_all":"every one of the {count} covers that follow the profile","panel.profile.edit.reach_one":"1 cover","panel.profile.edit.title":"Edit the values","panel.profile.followers.adjusted":"adjusted: own values for {keys}","panel.profile.followers.count":"{count} covers follow it","panel.profile.followers.count_one":"1 cover follows it","panel.profile.followers.inherited":"inherited","panel.profile.followers.measured":"measured: nothing inherited","panel.profile.followers.none":"No cover follows it.","panel.profile.from_file":"Profile of the configuration file: read-only here.","panel.profile.impact.invalid":"correct the fields to see the preview","panel.profile.impact.kept":"own values stay: {keys}","panel.profile.impact.no_change":"no change: all values are its own","panel.profile.impact.no_travel":"travel not recorded: it will use the profile's values as they are","panel.profile.impact.state_adjusted":"adjusted: only the inherited values change","panel.profile.impact.state_inherited":"inherited: everything changes","panel.profile.impact.state_measured":"measured","panel.profile.impact.title":"Impact preview","panel.profile.name":"Profile «{profile}»","panel.profile.provenance":"Measured on {cover} · {date}","panel.profile.provenance_missing":"Where it was measured is not recorded.","panel.profile.provenance_now_none":"now follows no profile","panel.profile.provenance_now_profile":"now follows «{profile}»","panel.profile.reference_travel":"Reference travel","panel.profile.rename.action":"Rename","panel.profile.rename.field":"New name of the profile","panel.profile.rename.rule":"Letters, digits and underscores only, no more than 64 of them: no spaces, no accents — the name is also a key of the configuration file. The rename follows every cover that uses the profile.","panel.profile.rename.title":"Rename the profile","panel.profile.stored":"Stored profile","panel.profile.title":"Profile card","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.profile.values":"Values of the profile","panel.review.action.back":"Back to the overview","panel.review.action.confirm":"Confirm {count} assignments","panel.review.action.confirm_one":"Confirm 1 assignment","panel.review.action.missing_travel":"{count} travels missing","panel.review.action.missing_travel_one":"1 travel missing","panel.review.after":"After","panel.review.before":"Before","panel.review.intro":"The changes are written all at once. For each cover, this is what it will really use: the profile's values brought to its own travel.","panel.review.note.all_own":"It has values of its own for everything: nothing changes. The profile would only count for values removed later on.","panel.review.note.back_to_defaults":"The default values come back: the position in per cent will be a rough estimate. The travel and any value of its own stay.","panel.review.note.back_to_file":"The values of the configuration file come back. The travel and any value of its own stay.","panel.review.note.scaled":"Values of the profile «{profile}» (measured on {reference} cm) brought to a travel of {travel} cm.","panel.review.note.some_own":"It has some values of its own: those stay. Only the inherited values change.","panel.review.title":"Review and confirm","panel.review.travel.aria":"Curtain travel in centimetres","panel.review.travel.hint":"A profile is the measurement of one cover with a certain travel, and it is brought to the others in proportion. The travel of these is not known: measure the distance the bottom edge covers from fully closed to fully open, and write it in centimetres (decimals with a comma or with a point).","panel.review.travel.label":"Curtain travel","panel.review.travel.placeholder":"e.g. 145","panel.review.travel.required":"The travel is needed, in centimetres.","panel.review.travel.title":"How far does the curtain of these covers run?","panel.screen.completed":"Completed","panel.screen.motor":"Motor","panel.screen.new_text":"new text — not translated yet","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.position":"Estimated position","panel.screen.progress":"Positioning progress","panel.toast.action.undo":"Undo","panel.toast.assigned":"{count} assignments applied","panel.toast.assigned_one":"1 assignment applied","panel.toast.measure_removed":"Measurement removed: «{cover}» now uses {destination}.","panel.toast.order_saved":"The new order will be remembered.","panel.toast.profile_deleted":"Profile «{profile}» deleted: the covers go back to the file or to the defaults.","panel.toast.profile_renamed":"Renamed to «{profile}»: the rename follows every cover that uses it.","panel.toast.profile_saved":"Profile «{profile}» updated: {count} covers reached.","panel.toast.profile_saved_one":"Profile «{profile}» updated: 1 cover reached.","panel.toast.travel_saved":"The travel of «{cover}» is saved: the profile is brought to this measurement.","panel.toast.undone":"Changes undone: everything as it was.","panel.toast.values_saved":"The values of «{cover}» are saved: they beat the profile and the file.","panel.wizard.action.claim":"Take control","panel.wizard.action.claim_cancel":"Take control and end it","panel.wizard.action.end":"End the calibration","panel.wizard.action.exit":"Leave the calibration","panel.wizard.action.force":"End it anyway","panel.wizard.action.stop":"Stop the shutter","panel.wizard.action.submit":"That is right, go on","panel.wizard.announce.motor":"The motor has started.","panel.wizard.busy.end_other":"Close the dialog and free the shutter","panel.wizard.busy.end_other_confirm":"Close the Configure dialog open on this gateway? The unsaved measurements of that dialog are lost, and if it had saved something the integration is reloaded.","panel.wizard.busy.other":"«{cover}» is in calibration in the Configure dialog.","panel.wizard.busy.panel":"A guided calibration of «{cover}» is already running, in another panel or in another tab. It can be followed from here; taking control of it is a button on its screen.","panel.wizard.busy.service":"A calibration run started by an action is still under way: wait for it to finish.","panel.wizard.busy.title":"The shutter is already in calibration","panel.wizard.check.measured":"The tape read {measured} cm at {percent}% of the travel, where the model had predicted {predicted} cm.","panel.wizard.check.no_reference.body":"The tape read {measured} cm at {percent}% of the travel, but the values {cover} was following are no longer there, so there is no prediction to compare it with. The reading has not been thrown away: go on, and the review says what would be saved.","panel.wizard.check.no_reference.title":"There was nothing to check against","panel.wizard.check.threshold":"Above {threshold} cm it is worth measuring this shutter on its own rather than trusting the profile.","panel.wizard.check.threshold_profile":"Above {threshold} cm it is worth measuring this shutter on its own: the profile «{profile}» was itself checked to within {accuracy} cm.","panel.wizard.cue.toggle":"Buzz and beep when the motor starts","panel.wizard.exit.body":"Nothing is saved: the measurements taken so far are discarded. If the shutter is moving, the run under way finishes by itself at its end stop.","panel.wizard.exit.leave":"Leave without saving","panel.wizard.exit.stay":"Go on measuring","panel.wizard.exit.title":"Leave the calibration?","panel.wizard.external.moved":"The shutter has been moved by a command from outside. Nothing of this step depended on where it was, so the calibration goes on from here.","panel.wizard.external.reading":"The shutter was moved after it had been positioned: this reading no longer matches. Repeat the step.","panel.wizard.external.rehomed":"The shutter had been moved by a command from outside: it has been brought back to its end stop, and the measurement starts from there.","panel.wizard.motor.moving":"running for {seconds} s","panel.wizard.motor.position":"{percent}%","panel.wizard.motor.starting":"starting…","panel.wizard.motor.stopped":"stopped","panel.wizard.outcome.action.again":"Calibrate another shutter","panel.wizard.outcome.action.close":"Close","panel.wizard.outcome.action.open_cover":"Open the shutter's card","panel.wizard.outcome.cancelled.body":"Nothing has been saved: {cover} answers ordinary commands again. A run under way is not stopped and finishes by itself at its end stop.","panel.wizard.outcome.cancelled.title":"Calibration cancelled","panel.wizard.outcome.expired.body":"The calibration stood still for too long, so {cover} has been released and, if it was moving, stopped. Nothing has been saved.","panel.wizard.outcome.expired.title":"The session timed out","panel.wizard.outcome.gone.body":"{cover} is no longer in this gateway's configuration: the calibration has been closed without saving.","panel.wizard.outcome.gone.title":"The shutter is no longer there","panel.wizard.outcome.left.body":"The calibration was closed before the first measurement. Nothing has been saved.","panel.wizard.outcome.left.title":"The calibration was closed","panel.wizard.outcome.saved.cover":"{cover} is saved and already in use, with values of its own ({origin}).","panel.wizard.outcome.saved.profile":"{cover} is saved and already in use: it follows the profile «{profile}» ({origin}). Shutters like it are calibrated with route (B).","panel.wizard.outcome.saved.title":"Calibration saved","panel.wizard.outcome.unloaded.body":"A reload of the integration closed the calibration of {cover}. Nothing has been saved; if the shutter was moving it has been stopped.","panel.wizard.outcome.unloaded.title":"The integration was reloaded","panel.wizard.owner.other":"This calibration is being driven by another device.","panel.wizard.owner.take":"Take control","panel.wizard.phase.ascent":"Ascent","panel.wizard.phase.descent":"Descent","panel.wizard.phase.prepare":"Preparation","panel.wizard.phase.readings":"Tape readings","panel.wizard.phase.route":"Route","panel.wizard.phase.summary":"Summary","panel.wizard.pick.body":"Only the shutters whose position Home Assistant works out from their run times are listed: they are the only ones this calibration is about. The first time round it is worth choosing a shutter that is representative of its type and easy to measure.","panel.wizard.pick.title":"Which shutter is being measured?","panel.wizard.positioning.remaining":"About {seconds} s left","panel.wizard.positioning.title":"The shutter is being positioned","panel.wizard.press.registered":"Press registered ✓","panel.wizard.press.registered_note":"Press registered at {seconds} s: the shutter has been stopped.","panel.wizard.problem.interrupted.body":"During this step the shutter was stopped or moved by another command, so what the step was measuring no longer holds. Nothing has been written. Wait until the shutter is still and repeat the step.","panel.wizard.problem.interrupted.title":"The measurement was interrupted","panel.wizard.profile.from_file":"The values the configuration file writes for this shutter.","panel.wizard.profile.meta":"reference travel {reference} cm","panel.wizard.profile.meta_measured":"reference travel {reference} cm · measured on {cover}","panel.wizard.profile.meta_no_reference":"reference travel not given","panel.wizard.render_error.body":"The calibration is still running on the gateway and nothing has been lost. Try again, or end it.","panel.wizard.render_error.title":"This screen could not be drawn","panel.wizard.review.accuracy_checked":"Accuracy checked: within {accuracy} cm at {percent}% of the descent, in a position nothing was calculated on.","panel.wizard.review.accuracy_unchecked":"The accuracy has not been checked yet. The thorough calibration adds four readings and a check, about two minutes.","panel.wizard.review.affected_hide":"Hide the shutters that follow the profile","panel.wizard.review.affected_show":"Show the shutters that follow the profile","panel.wizard.review.intro":"Before saving: on the left what {cover} uses today, on the right what it will use afterwards. Nothing has been written yet.","panel.wizard.review.key.start_delay":"Start delay (s)","panel.wizard.review.key.stop_latency":"Stop delay (s)","panel.wizard.review.name_clash":"The configuration file defines «{profile}» as well: the measured profile takes precedence.","panel.wizard.review.profile_exists":"The profile «{profile}» already exists: saving updates it, and with it the shutters that follow it ({count}).","panel.wizard.review.save_cover_only":"Save for this shutter only","panel.wizard.review.save_profile":"Save as the profile «{profile}»","panel.wizard.review.side_effects":"Saving also changes values this calibration did not measure:","panel.wizard.review.title":"What was measured","panel.wizard.review.where":"Once saved, the values stay in Home Assistant and {cover} uses them at once, with no restart. They can be reviewed, corrected by hand or removed from the shutter's card in this panel.","panel.wizard.review.yaml":"The equivalent for myhome.yaml","panel.wizard.title":"Guided calibration","panel.wizard.trouble.freed":"If nothing works, the gateway releases the shutter by itself at {time}.","panel.wizard.trouble.freed_later":"If nothing works, the gateway releases the shutter by itself when the calibration's time runs out.","panel.wizard.trouble.title":"The calibration was not closed"};var kt=wi,Bo=Object.keys(kt);var Rr=/^\/myhome_static\/[A-Za-z0-9._~\-/]+$/,Er=/(^|\/)\.\.?(\/|$)/,Pe=n=>Rr.test(n)&&!Er.test(n),yi=/^[A-Za-z0-9 %.,\-]+$/,bi=n=>{if(!Pe(n.src))return null;let i=n.size&&yi.test(n.size)?n.size:"100% auto",e=n.pos&&yi.test(n.pos)?n.pos:"50% 60%";return{backgroundImage:`url("${n.src}")`,backgroundSize:i,backgroundPosition:e}};var xi=/^!\[([^\]]*)\]\(([^)\s]+)\)$/,Tr=/^!\[[^\]]*\]\([^)\s]*\)\s*\n\s*\n/,St=n=>{let i=Tr.exec(n||"");if(!i)return{image:null,body:n||""};let e=i[0].trim(),t=xi.exec(e);return!t||!Pe(t[2])?{image:null,body:n||""}:{image:{alt:t[1],src:t[2]},body:(n||"").slice(i[0].length)}},ze=n=>{let i=[],e=n.split("**"),t=e.length%2===0;return e.forEach((r,o)=>{if(!r)return;let s=o%2===1&&!(t&&o===e.length-1);i.push(s?a`<strong>${r}</strong>`:a`<span>${r}</span>`)}),i},Cr=n=>/^\s*[-*]\s+/.test(n),J=n=>{let i=(n||"").replace(/\r\n/g,`
`).split(/\n{2,}/),e=[];for(let t of i){let r=t.trim();if(!r)continue;let o=xi.exec(r);if(o){e.push(Pe(o[2])?a`<img class="md-image" src=${o[2]} alt=${o[1]} />`:a`<p>${ze(o[1])}</p>`);continue}let s=r.split(`
`);if(s.every(Cr)){e.push(a`<ul>
          ${s.map(l=>a`<li>${ze(l.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}e.push(a`<p>
        ${s.map((l,c)=>c===0?ze(l):[a`<br />`,...ze(l)])}
      </p>`)}return a`${e}`};var b=n=>n&&typeof n=="object"&&"code"in n?n:{code:"unknown_error",message:String(n)},$i=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/overview",...i?{entry_id:i}:{}}),ki=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/texts",language:i}),Si=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_detail",entry_id:i,cover_unique_id:e}),Ie=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/preview",entry_id:i,items:e,...t?{profile_values:t}:{}}),Ri=(n,i,e)=>n.subscribeMessage(e,{type:"myhome/calibration/subscribe",...i?{entry_id:i}:{}}),me=n=>b(n).code==="unknown_command",Ei=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/assign",entry_id:i,assignments:e,...t?{order:t}:{}}),Ti=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/reorder",entry_id:i,order:e,...t!==void 0?{profile:t}:{}}),Ci=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/set_travel",entry_id:i,cover_unique_id:e,height:t}),Ai=(n,i,e,t,r)=>n.sendMessagePromise({type:"myhome/calibration/cover_edit",entry_id:i,cover_unique_id:e,overrides:t,...r!==void 0?{height:r}:{}}),Pi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_forget",entry_id:i,cover_unique_id:e}),zi=(n,i,e,t,r)=>n.sendMessagePromise({type:"myhome/calibration/profile_edit",entry_id:i,name:e,values:t,reference_height:r}),Ii=(n,i,e,t)=>n.sendMessagePromise({type:"myhome/calibration/profile_rename",entry_id:i,name:e,new_name:t}),Mi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/profile_delete",entry_id:i,name:e}),Oi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/undo",entry_id:i,undo_token:e}),Li=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/session/get",entry_id:i}),Di=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/start",entry_id:i,cover_unique_id:e.cover_unique_id,client_id:e.client_id,...e.path?{path:e.path}:{},...e.profile?{profile:e.profile}:{},...e.scope?{scope:e.scope}:{}}),Hi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/attach",entry_id:i,session_id:e.session_id,client_id:e.client_id,...e.claim?{claim:!0}:{}}),Fi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/heartbeat",entry_id:i,session_id:e.session_id,client_id:e.client_id}),Ni=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/act",entry_id:i,session_id:e.session_id,client_id:e.client_id,revision:e.revision,action:e.action,...e.value===void 0?{}:{value:e.value}}),Wi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/stop",entry_id:i,session_id:e.session_id,client_id:e.client_id}),qi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/leave",entry_id:i,session_id:e.session_id,client_id:e.client_id}),Bi=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/cancel",entry_id:i,client_id:e.client_id,...e.session_id?{session_id:e.session_id}:{},...e.force?{force:!0}:{}}),Ui=(n,i,e)=>n.sendMessagePromise({type:"myhome/calibration/session/save",entry_id:i,session_id:e.session_id,client_id:e.client_id,revision:e.revision,target:e.target}),Ki=(n,i)=>n.sendMessagePromise({type:"myhome/calibration/session/end_other",entry_id:i});var Ar=/\{([A-Za-z0-9_]+)\}/g,Me=(n,i)=>i?n.replace(Ar,(e,t)=>Object.prototype.hasOwnProperty.call(i,t)?String(i[t]):e):n,Pr=/[“”„"‹›«»][\s  ]*(\{[A-Za-z0-9_]+\})[\s  ]*[“”„"‹›«»]/gu,Gi=n=>n.replace(Pr,"«$1»"),y=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this._times=null;this.language="en";this.loaded=!1}async load(i,e){let t=await ki(i,e);this._texts=t.texts??{},this.language=t.language,this.loaded=!0,this._numbers.clear(),this._dates=null,this._times=null}t(i,e){let t=this._lookup(i);if(t!==null)return Me(t,e);let r=kt[i];return Me(r??i,e)}md(i,e){return J(this.t(i,e))}refusal(i,e){let t=i?this._lookup(`exceptions.${i}.message`):null;return t!==null?Me(Gi(t),e):this.t("panel.error.not_found")}origin(i,e){let t=`selector.calibration_origin.options.${i}`;return Me(Gi(this._lookup(t)??t),{profile:e??""})}number(i,e){let t=this._numbers.get(e);return t||(t=new Intl.NumberFormat(this.language,{minimumFractionDigits:e,maximumFractionDigits:e}),this._numbers.set(e,t)),t.format(i)}date(i){let e=new Date(i);return Number.isNaN(e.getTime())?i:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(e))}time(i){let e=new Date(i);return Number.isNaN(e.getTime())?i:(this._times||(this._times=new Intl.DateTimeFormat(this.language,{timeStyle:"short"})),this._times.format(e))}_lookup(i){let e=this._texts;for(let t of i.split(".")){if(e===null||typeof e!="object")return null;e=e[t]}return typeof e=="string"?e:null}};var ji=n=>typeof customElements<"u"&&customElements.get(n)!==void 0;var Vi=n=>{n.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var Oe=(n,i)=>{let e=Le(n.unique_id,i);return e?e.to:n.profile??null},Le=(n,i)=>i.find(e=>e.cover===n),Yi=(n,i)=>i===null?n.t("panel.assign.target_none"):n.t("panel.assign.pending.route_name",{profile:i}),Xi=(n,i,e)=>n.t("panel.assign.pending.route",{from:Yi(n,i),to:Yi(n,e)}),Zi=(n,i,e)=>{let t=n.filter(r=>r.cover!==i.unique_id);return e===(i.profile??null)?{pending:t,withdrawn:!0}:{pending:[...t,{cover:i.unique_id,to:e}],withdrawn:!1}},Qi=(n,i)=>{let e=new Map(n.covers.map(o=>[o.unique_id,o]));if(!i)return[...n.covers].sort((o,s)=>o.order_index-s.order_index);let t=new Set,r=[];for(let o of i){let s=e.get(o);s&&!t.has(o)&&(t.add(o),r.push(s))}for(let o of n.covers)t.has(o.unique_id)||r.push(o);return r},Rt=(n,i,e)=>{let t=n.filter(o=>o!==i),r=t.length;if(e.beforeId){let o=t.indexOf(e.beforeId);r=o<0?t.length:o}else if(e.afterId){let o=t.indexOf(e.afterId);r=o<0?t.length:o+1}return[...t.slice(0,r),i,...t.slice(r)]},Ji=(n,i,e)=>{let t=e.filter(r=>r!==i).at(-1)??null;return Rt(n,i,{beforeId:null,afterId:t})},Et=(n,i,e)=>{let t=new Set(e.map(r=>r.unique_id));return n.filter(r=>t.has(r.cover)).map(r=>{let o=i[r.cover],s=o===void 0?void 0:I(o);return{cover_unique_id:r.cover,profile:r.to,...s==null?{}:{height:s}}})},I=n=>{let i=n.trim().replace(",",".");if(!i)return null;let e=Number(i);return Number.isFinite(e)?e:null},zr=20,Ir=500,ve=n=>{if(n===void 0||n.trim()==="")return"missing_travel";let i=I(n);return i===null?"not_a_number":i<zr||i>Ir?"out_of_range":null},Tt=n=>({cover_unique_id:n.unique_id,profile:n.profile_from_file?null:n.profile??null}),en=(n,i)=>i.to!==null&&n.height===null,M=["opening_time","closing_time","slat_time","opening_roll","closing_roll"],fe=["opening_time","closing_time","slat_time"],ge=["opening_roll","closing_roll"],De=["slat_time",...ge],O={opening_time:1,closing_time:1,slat_time:1,opening_roll:2,closing_roll:2};var L={opening_time:{min:1,max:600,decimals:1},closing_time:{min:1,max:600,decimals:1},slat_time:{min:0,max:60,decimals:1},opening_roll:{min:1,max:5,decimals:2},closing_roll:{min:1,max:5,decimals:2},height:{min:20,max:500,decimals:0},reference_height:{min:20,max:500,decimals:0}},ee={opening_time:"panel.common.unit.seconds",closing_time:"panel.common.unit.seconds",slat_time:"panel.common.unit.seconds",opening_roll:null,closing_roll:null,height:"panel.common.unit.centimetres",reference_height:"panel.common.unit.centimetres"},F=n=>n.replace(/\s*\([^()]*\)\s*$/u,""),j=(n,i)=>i?`${n} ${i}`:n,x=(n,i)=>{let e=(i??"").trim();if(e==="")return null;let t=I(e);if(t===null)return"not_a_number";let r=L[n];return r&&(t<r.min||t>r.max)?"out_of_range":null},C=n=>(n??"").trim()==="";var N="/config/integrations/integration/myhome";var Ct="dialog-data-entry-flow",Mr=()=>typeof customElements<"u"&&customElements.get(Ct)!==void 0,tn=n=>{history.pushState(null,"",n),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))},nn=n=>Mr()?(n.source.dispatchEvent(new CustomEvent("show-dialog",{bubbles:!0,composed:!0,detail:{dialogTag:Ct,dialogImport:()=>Promise.resolve(),dialogParams:{startFlowHandler:n.entryId,domain:"myhome"}}})),setTimeout(()=>{document.querySelector(Ct)||(n.onLeaving(),tn(N))},400),"waiting"):(n.onLeaving(),tn(N),"page");var V=n=>n.view==="cover"||n.view==="profile",rn=(n,i,e)=>!V(e)||!V(i)?null:i.path===e.path?n:n&&n.path===e.path?null:i,on=n=>n?.path??"/";var Or={view:"overview",params:{},path:"/"},sn=n=>{let i="/"+(n||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(i==="/")return Or;let e=i.slice(1).split("/"),t=e.slice(1).join("/"),r=t;try{r=decodeURIComponent(t)}catch{}return e[0]==="cover"&&t?{view:"cover",params:{id:r},path:i}:e[0]==="profile"&&t?{view:"profile",params:{name:r},path:i}:e[0]==="calibrate"?{view:"calibrate",params:{},path:"/calibrate"}:{view:"unknown",params:{},path:i}},an=(n,i)=>n==="calibrate"?"/calibrate":!i||n!=="cover"&&n!=="profile"?"/":`/${n}/${encodeURIComponent(i)}`,He=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(i){this._onChange=i,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(i){let e=i||"/";if(e===this._fromHost)return;let t=this.current.path;this._fromHost=e,this.current.path!==t&&this._emit()}get current(){let i=typeof location<"u"?location.hash:"";return i&&i.length>1?sn(i.slice(1)):sn(this._fromHost)}navigate(i){let e="#"+(i.startsWith("/")?i:"/"+i);location.hash!==e&&(location.hash=e)}_emit(){this._onChange(this.current)}};var Lr=15e3,ln="myhome-calibration-client",dn=/^[A-Za-z0-9-]{8,64}$/,_e=n=>n!==null&&(n.state==="saved"||n.state==="ended"),At=n=>n.translation_key??n.code,Pt=new Set(["unknown_session","session_ended"]),Dr=new Set(["unknown_entry","entry_not_loaded"]),Hr=()=>{try{let i=globalThis.crypto?.randomUUID?.();if(i&&dn.test(i))return i}catch{}return`c-${`${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`}`.replace(/[^A-Za-z0-9-]/g,"").slice(0,64).padEnd(8,"0")},Fr=()=>{try{return globalThis.sessionStorage??null}catch{return null}},Nr=n=>{try{let e=n?.getItem(ln);if(e&&dn.test(e))return e}catch{}let i=Hr();try{n?.setItem(ln,i)}catch{}return i},Fe=class{constructor(i){this._session=null;this._capabilities=null;this._owner=!1;this._attachedTo=null;this._timer=null;this._disposed=!1;this._warned=!1;this._connection=i.connection,this.entryId=i.entryId,this._onChange=i.onChange??(()=>{}),this.clientId=i.clientId??Nr(i.storage===void 0?Fr():i.storage)}get session(){return this._session}get capabilities(){return this._capabilities}get owner(){return this._owner}get beating(){return this._timer!==null}async get(){try{let i=await Li(this._connection,this.entryId);return this._capabilities=i.capabilities??this._capabilities,this._adopt(i.session),this._done(i.session)}catch(i){return this._failed(i)}}async start(i){try{let e=await Di(this._connection,this.entryId,{cover_unique_id:i.cover,client_id:this.clientId,path:i.path,profile:i.profile,scope:i.scope});return this._attachedTo=e.session?.session_id??null,this._adopt(e.session),this._done(e.session)}catch(e){return this._failed(e)}}async attach(i,e=!1){try{let t=await Hi(this._connection,this.entryId,{session_id:i,client_id:this.clientId,claim:e});return this._attachedTo=t.session?.session_id??null,this._adopt(t.session),this._done(t.session)}catch(t){return this._failed(t)}}async act(i,e){let t=this._session;if(!t)return this._failed({code:"not_found",message:"no session",translation_key:"unknown_session"});try{let r=await Ni(this._connection,this.entryId,{session_id:t.session_id,client_id:this.clientId,revision:t.revision,action:i,value:e});return this._adopt(r.session),this._done(r.session)}catch(r){return this._failed(r)}}async stop(){let i=this._session;if(!i)return this._failed({code:"not_found",message:"no session",translation_key:"unknown_session"});try{let e=await Wi(this._connection,this.entryId,{session_id:i.session_id,client_id:this.clientId});return this._adopt(e.session),this._done(e.session)}catch(e){return this._failed(e)}}async save(i){let e=this._session;if(!e)return this._failed({code:"not_found",message:"no session",translation_key:"unknown_session"});try{let t=await Ui(this._connection,this.entryId,{session_id:e.session_id,client_id:this.clientId,revision:e.revision,target:i});return this._adopt(t.session),{ok:!0,session:t.session,overview:t.overview??null}}catch(t){return this._failed(t)}}async leave(){let i=this._session;if(this._stopHeartbeat(),this._attachedTo=null,!i)return this._done(null);try{let e=await qi(this._connection,this.entryId,{session_id:i.session_id,client_id:this.clientId});return this._adopt(e.session),this._done(e.session)}catch(e){return this._failed(e)}}async endOther(){try{let i=await Ki(this._connection,this.entryId);return{ok:!0,flowsAborted:i.flows_aborted,stillCalibrating:i.still_calibrating,overview:i.overview??null}}catch(i){return this._failed(i)}}async cancel({force:i=!1}={}){let e=this._session;try{let t=await Bi(this._connection,this.entryId,{client_id:this.clientId,session_id:e?.session_id,force:i});return this._stopHeartbeat(),this._attachedTo=null,this._adopt(t.session),{ok:!0,branch:t.already_ended?"already_ended":"cancelled",session:t.session,error:null,recovery:[],freedAt:null}}catch(t){let r=b(t),o=At(r);if(o==="session_owned")return{ok:!1,branch:"owned",session:this._session,error:r,recovery:["claim_cancel","force"],freedAt:this._session?.idle_expires_at??null};if(Pt.has(o))return this._stopHeartbeat(),this._attachedTo=null,{ok:!0,branch:"gone",session:this._session,error:r,recovery:[],freedAt:null};let s=this._session?.idle_expires_at??null;return{ok:!1,branch:"unconfirmed",session:this._session,error:r,recovery:i&&s?["wait"]:["retry","force"],freedAt:s}}}async takeControl(){let i=this._session;return i?this.attach(i.session_id,!0):this._failed({code:"not_found",message:"no session",translation_key:"unknown_session"})}async claimAndCancel(){let i=this._session;if(!i)return this.cancel({force:!0});let e=await this.attach(i.session_id,!0);return e.ok?this.cancel():{ok:!1,branch:"unconfirmed",session:this._session,error:e.error,recovery:["force"],freedAt:this._session?.idle_expires_at??null}}apply(i){this._adopt(i)}async resume(){return this._attachedTo&&this._beat(),this.get()}dispose(){this._disposed=!0,this._stopHeartbeat(),this._attachedTo=null,this._onChange=()=>{}}_startHeartbeat(){this._timer!==null||this._disposed||!this._session||_e(this._session)||(this._timer=setInterval(()=>{this._beat()},Lr))}_stopHeartbeat(){this._timer!==null&&(clearInterval(this._timer),this._timer=null)}async _beat(){let i=this._session;if(!i||_e(i)){this._stopHeartbeat();return}try{let t=(await Fi(this._connection,this.entryId,{session_id:i.session_id,client_id:this.clientId})).owner===!0;t!==this._owner&&(this._owner=t,this._notify())}catch(e){let t=At(b(e));if(Pt.has(t)){this._stopHeartbeat(),this._attachedTo=null;return}}}_adopt(i){this._session=i,this._owner=i?.owner?.client_id===this.clientId,i===null||_e(i)||i.session_id!==this._attachedTo?(this._stopHeartbeat(),i?.session_id!==this._attachedTo&&(this._attachedTo=null)):this._startHeartbeat(),this._notify()}_notify(){try{this._onChange(this._session)}catch(i){this._warned||(this._warned=!0,console.error("MyHOME panel: the calibration screen threw while it was being told",i))}}_done(i){return{ok:!0,session:i,overview:null}}_failed(i){let e=b(i),t=At(e),r=["retry"];return t==="session_owned"?r=["claim"]:t==="revision_conflict"||Pt.has(t)||t==="already_calibrating"?r=["reload"]:Dr.has(t)&&(r=["retry"]),{ok:!1,error:e,recovery:r,freedAt:this._session?.idle_expires_at??null}}};var zt=["route","prepare","ascent","descent","readings","summary"],cn={route:"panel.wizard.phase.route",prepare:"panel.wizard.phase.prepare",ascent:"panel.wizard.phase.ascent",descent:"panel.wizard.phase.descent",readings:"panel.wizard.phase.readings",summary:"panel.wizard.phase.summary"},It={path:{template:"scelta",phase:"route"},path_a:{template:"lettura",phase:"prepare"},path_b:{template:"scelta",phase:"route"},path_c:{template:"scelta",phase:"route"},refine_scope:{template:"scelta",phase:"route"},home_closed:{template:"pos",phase:"prepare",stoppable:!0},home_closed_done:{template:"controllo",phase:"prepare"},open_timed:{template:"pos",phase:"ascent",stoppable:!0},open_brief:{template:"lettura",phase:"ascent",cue:!0},open_start:{template:"click",phase:"ascent",display:"open_lift",press:"starting",stoppable:!0},open_lift:{template:"click",phase:"ascent",press:"moving",stoppable:!0},lift_stop:{template:"click",phase:"ascent",display:"open_lift",press:"registered"},lift_check:{template:"controllo",phase:"ascent"},lift_check_late:{template:"controllo",phase:"ascent",display:"lift_check"},lift_gap:{template:"controllo",phase:"ascent"},lift_early:{template:"controllo",phase:"ascent"},open_home_again:{template:"pos",phase:"ascent",stoppable:!0},closed_again:{template:"controllo",phase:"ascent"},open_full_brief:{template:"lettura",phase:"ascent",cue:!0},open_full_start:{template:"click",phase:"ascent",display:"open_top",press:"starting",stoppable:!0},open_top:{template:"click",phase:"ascent",press:"moving",stoppable:!0},open_result:{template:"lettura",phase:"ascent"},open_result_gap:{template:"lettura",phase:"ascent"},height_read:{template:"pos",phase:"readings",stoppable:!0},height:{template:"metro",phase:"readings"},height_result:{template:"lettura",phase:"readings"},close_timed:{template:"pos",phase:"descent",stoppable:!0},close_brief:{template:"lettura",phase:"descent",cue:!0},close_start:{template:"click",phase:"descent",display:"close_bottom",press:"starting",stoppable:!0},close_bottom:{template:"click",phase:"descent",press:"moving",stoppable:!0},close_result:{template:"lettura",phase:"descent"},tape_brief:{template:"lettura",phase:"readings"},half_down:{template:"pos",phase:"readings",stoppable:!0},half_up:{template:"pos",phase:"readings",stoppable:!0},quarter_down:{template:"pos",phase:"readings",stoppable:!0},three_quarter_down:{template:"pos",phase:"readings",stoppable:!0},quarter_up:{template:"pos",phase:"readings",stoppable:!0},three_quarter_up:{template:"pos",phase:"readings",stoppable:!0},verify:{template:"pos",phase:"readings",stoppable:!0},verify_b:{template:"pos",phase:"readings",stoppable:!0},tape_run:{template:"pos",phase:"readings",stoppable:!0},measure_descent:{template:"metro",phase:"readings"},measure_ascent:{template:"metro",phase:"readings"},tape_result:{template:"lettura",phase:"readings"},measure_verify:{template:"metro",phase:"readings"},verify_result:{template:"controllo",phase:"readings"},verify_offer:{template:"controllo",phase:"readings"},profile_name:{template:"metro",phase:"summary"},summary_basic:{template:"riepilogo",phase:"summary",own:!0},summary_short:{template:"riepilogo",phase:"summary",own:!0},summary_correction:{template:"riepilogo",phase:"summary",own:!0},summary_precise:{template:"riepilogo",phase:"summary",own:!0},problem_no_echo:{template:"esito",phase:null},problem_not_delivered:{template:"esito",phase:null},problem_not_stopped:{template:"esito",phase:null},problem_busy:{template:"esito",phase:null},problem_bad_point:{template:"esito",phase:null},problem_timeout:{template:"esito",phase:null},problem_unknown:{template:"esito",phase:null},problem_interrupted:{template:"esito",phase:null,own:!0}};var Wr={run:1,slat:1,gap:1,height:1,measured:1,accuracy:1,deviation:1,expected:0,tolerance:0,percent:0,readings:0},qr={travel_cm:0,opening_time_s:1,closing_time_s:1,slat_time_s:1,opening_roll:2,closing_roll:2,stop_latency_s:2,start_delay_s:2},Br={travel_cm:"cm",opening_time_s:"s",closing_time_s:"s",slat_time_s:"s",opening_roll:"",closing_roll:"",stop_latency_s:"s",start_delay_s:"s"},Ur={travel_cm:"height",opening_time_s:"opening_time",closing_time_s:"closing_time",slat_time_s:"slat_time",opening_roll:"opening_roll",closing_roll:"closing_roll"},Mt=(n,i)=>{let e=Ur[n];return e?i.t(`options.step.calibration_edit.data.${e}`):n==="stop_latency_s"?i.t("panel.wizard.review.key.stop_latency"):i.t("panel.wizard.review.key.start_delay")},we=(n,i,e)=>{if(i===null)return"—";let t=e.number(i,qr[n]??1),r=Br[n]??"";if(r==="")return t;let o=r==="cm"?e.t("panel.common.unit.centimetres"):e.t("panel.common.unit.seconds");return`${t} ${o}`},pn=(n,i,e)=>{let t={};for(let[r,o]of Object.entries({...n,...e??{}}))o==null?t[r]="":typeof o=="number"?t[r]=i.number(o,Wr[r]??1):t[r]=o;return t},Ot=(n,i)=>i.number(n,1),Lt=(n,i,e)=>{let t=Date.parse(n);return Number.isNaN(t)?0:Math.max(0,(e-i-t)/1e3)},hn=(n,i)=>n===null?0:Math.max(0,n-i),un=(n,i)=>n===null||n<=0?0:Math.max(0,Math.min(1,i/n));var D="act:",ye="save:",be="pick:",Ht="submit",Ft="stop",Nt="claim",Wt="cue",qt="show:all",Bt="show:affected",qe="again",Ut="open_cover",te="close",Dt=["travel_cm","opening_time_s","closing_time_s"],Kr={repeat_step:"home_closed_done",not_right:"home_closed_done",accept_step:"open_result",repeat_tape:"tape_result",tape_not_right:"tape_result",repeat_measure:"height_result",path_c:"verify_result",refine:"summary_basic"},T=(n,i,e)=>{let t=n.t(i,e);return t===i?null:t},ie=(n,i,e,t)=>{let r=T(n,`options.step.${i}.menu_options.${e}`,t);if(r!==null)return r;let o=Kr[e];return(o?T(n,`options.step.${o}.menu_options.${e}`,t):null)??e},vn=(n,i)=>{let e=n?.step,t=e?It[e]:void 0;return t?.phase?i.t("panel.screen.phase",{phase:i.t(cn[t.phase]),index:zt.indexOf(t.phase)+1,count:zt.length}):null},Ne=(n,i,e)=>{let t=n.find(r=>r.key===i);return t?{label:Mt(i,e),before:t.before===null?void 0:we(i,t.before,e),after:we(i,t.after,e)}:null},fn=(n,i)=>{let{i18n:e}=i,t=pn(n.placeholders,e);if(!n.cover||typeof n.cover.name!="string")throw new Error("the snapshot names no shutter");if(n.state==="saved"||n.state==="ended")return io(n,i,t);let r=n.step;if(!r)throw new Error(`a running session with no step (state ${n.state})`);let o=It[r];if(!o)throw new Error(`no screen is described for the step '${r}'`);let s=o.template==="pos"?Qr(n,i,o,t):o.template==="riepilogo"?Jr(n,i,t):o.template==="esito"?to(n,i,o,t):Gr(n,i,o,r,t);return no(s,n,i),s},Gr=(n,i,e,t,r)=>{let{i18n:o}=i,s=e.display??t,l=T(o,`options.step.${s}.title`,r)??"",c=T(o,`options.step.${s}.description`,r)??"",{image:p,body:u}=St(c),h={id:t,model:e.template,title:l,body:u,image:p?{src:p.src,alt:p.alt}:void 0};return e.template==="click"?jr(h,n,i,e,t,u,r):(e.template==="metro"||e.template==="controllo"&&n.form)&&Yr(h,n,i,t,r),(e.template==="scelta"||e.template==="controllo")&&(h.options=Xr(n,i,t,r)),n.check&&Vr(h,n,i),e.template==="metro"&&n.actions.length>0&&(h.secondary=n.actions.map(v=>({label:ie(o,t,v,r),action:`${D}${v}`,kind:"secondary"}))),h.primary||gn(h,n,i,t,r),e.cue&&(h.toggle={label:o.t("panel.wizard.cue.toggle"),checked:i.cue,action:Wt}),h},jr=(n,i,e,t,r,o,s)=>{let{i18n:l}=e,c=i.movement,p=c?T(l,`options.progress.${c.progress_action}`,s):null,u=c?.started_at??null,h=u?Lt(u,e.skewMs,e.now):0,v=o.split(/\n{2,}/).map(f=>f.trim()).filter(f=>f!==""),_=t.press==="moving"?v[v.length-1]??"":p??"";t.press==="moving"||t.press==="registered"?n.body=v.slice(0,-1).join(`

`):n.body="";let E=e.position===null?void 0:l.t("panel.wizard.motor.position",{percent:l.number(e.position,0)});if(t.press==="starting"){n.press={state:"starting",label:"",instruction:_,motor:l.t("panel.wizard.motor.starting"),position:E},n.primary={label:"…",action:"",disabled:!0,kind:"primary"},We(n,t,l);return}if(t.press==="registered"){let Jt=i.measured.lift?.pressed_at??null,ei=Jt&&u?Math.max(0,(Date.parse(Jt)-Date.parse(u))/1e3):null;n.press={state:"registered",label:"",instruction:_,motor:l.t("panel.wizard.motor.stopped"),position:E,note:ei===null?void 0:l.t("panel.wizard.press.registered_note",{seconds:Ot(ei,l)})},n.primary={label:l.t("panel.wizard.press.registered"),action:"",disabled:!0,kind:"primary"},We(n,t,l);return}let X=i.actions[0];n.press={state:"moving",label:"",instruction:_,motor:l.t("panel.wizard.motor.moving",{seconds:Ot(h,l)}),position:E},X&&(n.primary={label:ie(l,r,X,s),action:`${D}${X}`,kind:"primary"}),n.secondary=i.actions.slice(1).map(f=>({label:ie(l,r,f,s),action:`${D}${f}`,kind:"secondary"})),We(n,t,l)},We=(n,i,e)=>{i.stoppable&&(n.secondary=[...n.secondary??[],{label:e.t("panel.wizard.action.stop"),action:Ft,kind:"text"}])},Vr=(n,i,e)=>{let{i18n:t}=e,r=i.check;if(!r)return;let o=t.number(r.fraction*100,0);if(r.gap_cm===null){n.title=t.t("panel.wizard.check.no_reference.title"),n.body=t.t("panel.wizard.check.no_reference.body",{cover:i.cover.name,measured:t.number(r.measured_cm,1),percent:o}),n.image=void 0;return}let s=[t.t("panel.wizard.check.measured",{measured:t.number(r.measured_cm,1),predicted:t.number(r.predicted_cm,1),percent:o})];r.threshold_cm!==null&&s.push(r.profile_check_cm===null?t.t("panel.wizard.check.threshold",{threshold:t.number(r.threshold_cm,0)}):t.t("panel.wizard.check.threshold_profile",{threshold:t.number(r.threshold_cm,0),profile:i.profile??"",accuracy:t.number(r.profile_check_cm,1)})),n.lines=s},Yr=(n,i,e,t,r)=>{let{i18n:o}=e,s=i.form;if(!s||s.kind==="choice")return;let l=s.field,c=T(o,`options.step.${t}.data.${l}`,r)??l,p=T(o,`options.step.${t}.data_description.${l}`,r)??void 0,u=s.suggested;n.field={label:c,hint:p,unit:s.unit??void 0,value:e.typed??"",placeholder:u==null?void 0:typeof u=="number"?o.number(u,1):u,error:s.error===null?void 0:T(o,`options.error.${s.error}`)??void 0,big:s.kind==="number",inputMode:s.kind==="text"?"text":"decimal"},n.primary={label:o.t("panel.wizard.action.submit"),action:Ht,kind:"primary"}},Xr=(n,i,e,t)=>{let{i18n:r}=i,o=n.form;return o?.kind==="choice"?(o.choices??[]).map(s=>Zr(s,i,o.suggested)):n.actions.map(s=>({title:ie(r,e,s,t),action:`${D}${s}`,current:n.intent?.scope!==void 0&&n.intent.scope===s}))},Zr=(n,i,e)=>{let{i18n:t}=i;if(n==="from_the_file")return{title:t.origin("from_the_file",null),meta:t.t("panel.wizard.profile.from_file"),action:`${be}${n}`,current:e===n};let r=i.profiles.find(c=>c.name===n),o=r?.reference_height??null,s=r?.measured_on_name??null,l=o===null?t.t("panel.wizard.profile.meta_no_reference"):s===null?t.t("panel.wizard.profile.meta",{reference:t.number(o,0)}):t.t("panel.wizard.profile.meta_measured",{reference:t.number(o,0),cover:s});return{title:n,meta:l,action:`${be}${n}`,current:e===n}},gn=(n,i,e,t,r)=>{let{i18n:o}=e;if(n.options&&n.options.length>0)return;let s=i.actions.map(c=>({label:ie(o,t,c,r),action:`${D}${c}`})),l=s[0];l&&(n.primary={...l,kind:"primary"},n.secondary=s.slice(1).map(c=>({...c,kind:"secondary"})))},Qr=(n,i,e,t)=>{let{i18n:r}=i,o=n.movement,s=o?T(r,`options.progress.${o.progress_action}`,t):null,l=o?.started_at??null,c=l?Lt(l,i.skewMs,i.now):0,p=o?.planned_s??null,u=hn(p,c),h={id:n.step??"",model:"pos",title:r.t("panel.wizard.positioning.title"),progress:{text:s??"",fraction:un(p,c),eta:p===null?void 0:r.t("panel.wizard.positioning.remaining",{seconds:r.number(u,0)}),done:p!==null&&u<=0}};return We(h,e,r),h},Jr=(n,i,e)=>{let{i18n:t}=i,r=n.review;if(!r)throw new Error("a session in review with no review in it");let o=Dt.map(h=>Ne(r.rows,h,t)).filter(h=>h!==null),s=["slat_time_s","opening_roll","closing_roll"].map(h=>Ne(r.rows,h,t)).filter(h=>h!==null),l=[];r.accuracy_cm!==null&&r.check_fraction!==null?l.push(t.t("panel.wizard.review.accuracy_checked",{accuracy:t.number(r.accuracy_cm,1),percent:t.number(r.check_fraction*100,0)})):l.push(t.t("panel.wizard.review.accuracy_unchecked")),r.profile_exists&&r.profile_name&&l.push(t.t("panel.wizard.review.profile_exists",{profile:r.profile_name,count:r.affected.length})),r.name_clash==="file"&&r.profile_name&&l.push(t.t("panel.wizard.review.name_clash",{profile:r.profile_name})),l.push(t.t("panel.wizard.review.where",{cover:n.cover.name}));let c={id:n.step??"",model:"riepilogo",title:t.t("panel.wizard.review.title"),body:t.t("panel.wizard.review.intro",{cover:n.cover.name}),summary:{rows:o,more:i.showAll?s:void 0,sideEffects:i.showAll&&r.side_effects.length>0?{title:t.t("panel.wizard.review.side_effects"),rows:r.side_effects.map(h=>({label:Mt(h.key,t),before:h.before===null?void 0:we(h.key,h.before,t),after:we(h.key,h.after,t)}))}:void 0,affected:i.showAffected&&r.affected.length>0?r.affected.map(h=>({title:h.name,rows:Dt.map(v=>Ne(h.rows,v,t)).filter(v=>v!==null)})):void 0,code:i.showAll?r.yaml:void 0,codeLabel:i.showAll?t.t("panel.wizard.review.yaml"):void 0,lines:l,disclose:eo(r.affected.length>0,i,t)}},[p,...u]=r.targets;return p&&(c.primary={...mn(p,r.profile_name,t),kind:"primary"}),c.secondary=[...u.map(h=>({...mn(h,r.profile_name,t),kind:"secondary"})),...n.actions.map(h=>({label:ie(t,"summary_basic",h,e),action:`${D}${h}`,kind:"text"}))],c},mn=(n,i,e)=>n==="profile"?{label:e.t("panel.wizard.review.save_profile",{profile:i??""}),action:`${ye}profile`}:{label:e.t("panel.wizard.review.save_cover_only"),action:`${ye}cover_only`},eo=(n,i,e)=>{let t=[{label:i.showAll?e.t("panel.common.action.hide_all"):e.t("panel.common.action.show_all"),action:qt,open:i.showAll}];return n&&t.push({label:i.showAffected?e.t("panel.wizard.review.affected_hide"):e.t("panel.wizard.review.affected_show"),action:Bt,open:i.showAffected}),t},to=(n,i,e,t)=>{let{i18n:r}=i,o=n.step,s=e.own?r.t("panel.wizard.problem.interrupted.title"):T(r,`options.step.${o}.title`,t)??"",l=e.own?r.t("panel.wizard.problem.interrupted.body"):T(r,`options.step.${o}.description`,t)??"",{image:c,body:p}=St(l),u={id:o,model:"esito",outcome:"problem",title:s,body:p,image:c?{src:c.src,alt:c.alt}:void 0,alert:s};return gn(u,n,i,o,t),u},io=(n,i,e)=>{let{i18n:t}=i,r=n.outcome,o=r?.reason??"cancelled",s=n.cover.name,l={id:`outcome_${o}`,model:"esito",title:"",outcome:"cancelled"};if(o==="saved"){let c=t.origin(r?.origin??"measured",r?.profile??null);l.outcome="saved",l.title=t.t("panel.wizard.outcome.saved.title"),l.body=r?.profile?t.t("panel.wizard.outcome.saved.profile",{cover:s,profile:r.profile,origin:c}):t.t("panel.wizard.outcome.saved.cover",{cover:s,origin:c});let p=n.review;return p&&(l.summary={rows:Dt.map(u=>Ne(p.rows,u,t)).filter(u=>u!==null)}),l.primary={label:t.t("panel.wizard.outcome.action.again"),action:qe,kind:"primary"},l.secondary=[{label:t.t("panel.wizard.outcome.action.open_cover"),action:Ut,kind:"secondary"},{label:t.t("panel.wizard.outcome.action.close"),action:te,kind:"text"}],l}return o==="cancelled"?(l.title=t.t("panel.wizard.outcome.cancelled.title"),l.body=t.t("panel.wizard.outcome.cancelled.body",{cover:s})):o==="expired"?(l.outcome="expired",l.title=t.t("panel.wizard.outcome.expired.title"),l.body=t.t("panel.wizard.outcome.expired.body",{cover:s})):o==="unloaded"?(l.outcome="expired",l.title=t.t("panel.wizard.outcome.unloaded.title"),l.body=t.t("panel.wizard.outcome.unloaded.body",{cover:s})):o==="left"?(l.title=t.t("panel.wizard.outcome.left.title"),l.body=t.t("panel.wizard.outcome.left.body")):(l.outcome="problem",l.title=t.t("panel.wizard.outcome.gone.title"),l.body=t.t("panel.wizard.outcome.gone.body",{cover:s})),l.primary={label:t.t("panel.wizard.outcome.action.again"),action:qe,kind:"primary"},l.secondary=[{label:t.t("panel.wizard.outcome.action.close"),action:te,kind:"text"}],l},no=(n,i,e)=>{let{i18n:t}=e;i.notice==="rehomed"?n.note={text:t.t("panel.wizard.external.rehomed"),tone:"info"}:i.notice==="reading_stale"?n.note={text:t.t("panel.wizard.external.reading"),tone:"error"}:i.external_move&&(n.note={text:t.t("panel.wizard.external.moved"),tone:"info"}),i.substate==="awaiting_endpoint"&&(n.alert=t.t("panel.wizard.announce.motor")),n.announce=n.title,e.readOnly&&(n.primary=void 0,n.secondary=void 0,n.options=void 0,n.field=void 0,n.toggle=void 0,n.summary&&(n.summary={...n.summary,disclose:void 0}),n.readOnly={text:t.t("panel.wizard.owner.other"),label:t.t("panel.wizard.owner.take"),action:Nt})};var _n={ask:null,service:!1},xe={for:null,answer:null,loading:!1,error:null,mode:"view",form:{},errors:{},preview:null,previewing:!1},$e={for:null,mode:"view",form:{},errors:{},newName:"",nameError:"",impact:null,impacting:!1},Y=n=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:n,search:"",room:"",announce:"",pending:[],order:null,drag:null,armed:null,dialog:null,review:!1,heights:{},heightsForced:!1,showAll:!1,preview:null,previewing:!1,applying:!1,snack:null,writeError:null,detail:xe,profile:$e,session:null,sessionError:null,wizardIntent:null,clientId:"",busy:_n,wizardExit:!1}),Ue={pending:[],order:null,heights:{},heightsForced:!1,preview:null,previewing:!1,review:!1,writeError:null},Be=class{constructor(i){this._subscribers=new Set;this._state=Y(i)}get state(){return this._state}subscribe(i){return this._subscribers.add(i),()=>this._subscribers.delete(i)}set(i){this._state={...this._state,...i};for(let e of this._subscribers)e(this._state)}setOverview(i){this.set({overview:i,entryId:i.entry_id,status:"ready",error:null,...i.measuring===null?{busy:_n}:{}})}setError(i){this.set({status:"error",error:i})}announce(i){this.set({announce:""}),this.set({announce:i})}};var $=m`:host{--myhome-text-on-primary: var(--text-primary-color, #ffffff);--myhome-text-on-accent: #1a1a1a;--myhome-snack-action: var( --snack-action-color, color-mix(in srgb, var(--myhome-accent) 40%, var(--myhome-background)) );--myhome-primary: var(--primary-color, #03a9f4);--myhome-accent: var(--accent-color, #ff9800);--myhome-text: var(--primary-text-color, #212121);--myhome-text-soft: var(--secondary-text-color, #727272);--myhome-text-off: var(--disabled-text-color, #bdbdbd);--myhome-background: var(--primary-background-color, #fafafa);--myhome-background-soft: var(--secondary-background-color, #e5e5e5);--myhome-card: var(--card-background-color, #ffffff);--myhome-divider: var(--divider-color, rgba(0, 0, 0, .12));--myhome-error: var(--error-color, #db4437);--myhome-warning: var(--warning-color, #ffa600);--myhome-success: var(--success-color, #43a047);--myhome-info: var(--info-color, #039be5);--myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));--myhome-header-text: var(--app-header-text-color, #ffffff);--myhome-radius: var(--ha-card-border-radius, 12px);--myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, .14));--myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));--myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));--myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));--myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));--myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));--myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));--myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));--myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));--myhome-primary-ink: color-mix(in srgb, var(--myhome-primary) 50%, var(--myhome-text));--myhome-error-ink: color-mix(in srgb, var(--myhome-error) 50%, var(--myhome-text));--myhome-warning-ink: color-mix(in srgb, var(--myhome-warning) 50%, var(--myhome-text));--myhome-success-ink: color-mix(in srgb, var(--myhome-success) 50%, var(--myhome-text));--myhome-info-ink: color-mix(in srgb, var(--myhome-info) 50%, var(--myhome-text));--myhome-text-soft-ink: color-mix(in srgb, var(--myhome-text-soft) 50%, var(--myhome-text));--myhome-field-border: color-mix(in srgb, var(--myhome-text-soft) 80%, var(--myhome-card));--myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);display:block;min-height:100%;color:var(--myhome-text);background:var(--myhome-background)}*,*:before,*:after{box-sizing:border-box}:host * :focus-visible{outline:2px solid var(--myhome-primary-ink);outline-offset:2px}@media(prefers-reduced-motion:reduce){:host *{animation-duration:.001ms!important;transition-duration:.001ms!important}}`,k=m`.card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}`,S=m`.cta{min-height:48px;padding:0 24px;border-radius:24px;border:none;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font:inherit;font-size:15px;font-weight:500;cursor:pointer}.cta.secondary{background:transparent;border:1px solid var(--myhome-primary-ink);color:var(--myhome-primary-ink)}.cta.text{background:transparent;border:none;color:var(--myhome-primary-ink);padding:0 12px}.cta.destructive{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}.cta[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.cta.compact{min-height:44px;padding:0 18px;border-radius:22px;font-size:14px}`,W=m`.field{height:44px;border-radius:8px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:var(--myhome-text);padding:0 12px;font:inherit;font-size:14px}.field:disabled{color:var(--myhome-text-off)}`,ne=m`.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0}`;var Ge=n=>a`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${n}</div>`,yn=n=>a`<div class="sr-only" role="alert" aria-live="assertive" aria-atomic="true">${n}</div>`,B=n=>{requestAnimationFrame(()=>{let i=n();i&&i.focus()})},Ke=class{constructor(){this._source=null}remember(i){this._source=i instanceof HTMLElement?i:null}restore(){let i=this._source;this._source=null,i&&i.isConnected&&B(()=>i)}},q=class{constructor(){this._root=null;this._onKey=i=>{if(i.key!=="Tab"||!this._root)return;let e=wn(this._root);if(e.length===0){i.preventDefault(),this._root.focus();return}let t=e[0],r=e[e.length-1],o=Kt(this._root.getRootNode());i.shiftKey&&(o===t||o===this._root)?(i.preventDefault(),r.focus()):!i.shiftKey&&o===r&&(i.preventDefault(),t.focus())}}hold(i,e=!0){this.release(),this._root=i,i.addEventListener("keydown",this._onKey),e&&B(()=>wn(i)[0]??i)}release(){this._root?.removeEventListener("keydown",this._onKey),this._root=null}},ro='a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',wn=n=>{let i=[],e=t=>{for(let r of t.querySelectorAll("*"))r.matches(ro)&&i.push(r),r.shadowRoot&&e(r.shadowRoot)};return e(n),i.filter(t=>t.offsetParent!==null)},Kt=n=>{let i=n.activeElement;for(;i?.shadowRoot?.activeElement;)i=i.shadowRoot.activeElement;return i};var je=m`.sheet-backdrop{position:fixed;inset:0;background:#0006;z-index:50}.sheet{position:fixed;left:0;right:0;bottom:0;max-height:86vh;background:var(--myhome-card);color:var(--myhome-text);z-index:51;border-radius:16px 16px 0 0;box-shadow:var(--myhome-shadow);display:flex;flex-direction:column}@media(min-width:600px){.sheet{inset:0 0 0 auto;width:min(480px,100vw);max-height:none;border-radius:0}}.sheet .head{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--myhome-divider)}.sheet .head h2{margin:0;font-size:18px;font-weight:500;flex:1;min-width:0}.sheet .head button{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);font-size:20px;cursor:pointer;border-radius:24px}.sheet .body{flex:1;overflow:auto;padding:16px;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}`;var bn=[je,m`.sheet .head h2.named{font-size:19px;font-weight:700;color:var(--myhome-primary);overflow-wrap:anywhere}.sheet.drawer .body{padding:16px 16px 0;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px));background:var(--myhome-background)}`],xn=n=>{let{i18n:i}=n,e=()=>{n.applying||n.onClose()};return a`
    <div class="sheet-backdrop" aria-hidden="true" @click=${e}></div>
    <div
      class="sheet drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      data-drawer
      tabindex="-1"
    >
      <div class="head">
        <!--
          One control, and which one it is is the whole of the back stack a user can see:
          an arrow while a screen is remembered behind this one, a cross when the only
          thing behind is the list. Both do the same thing to the address bar - they
          navigate - so the browser's own back button lands in the same places.
        -->
        <button
          type="button"
          aria-label=${n.hasBack?i.t("panel.common.action.back"):i.t("panel.common.action.close")}
          title=${n.hasBack?i.t("panel.common.action.back"):i.t("panel.common.action.close")}
          ?disabled=${n.applying}
          @click=${e}
        >
          ${n.hasBack?"←":"✕"}
        </button>
        <h2 id="drawer-title" class="named">${n.title}</h2>
      </div>
      <div class="body">${n.content}</div>
    </div>
  `};var kn=m`.measuring{max-width:1200px;margin:16px auto 0;padding:12px 16px;border-radius:var(--myhome-radius);background:var(--myhome-warning-pastel);display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.measuring strong{color:var(--myhome-warning-ink);font-weight:500}.measuring .body{flex:1 1 320px;line-height:1.5}.measuring .links{display:flex;gap:16px;flex-wrap:wrap}.measuring a{color:var(--myhome-primary-ink);min-height:44px;display:inline-flex;align-items:center}.measuring button.offer{min-height:44px;padding:0;border:none;background:none;font:inherit;font-size:inherit;color:var(--myhome-primary-ink);text-decoration:underline;cursor:pointer}.measuring button.offer.destructive{color:var(--myhome-error-ink)}`,re=(n,i,e,t=!1)=>a`<button
    class="offer ${t?"destructive":""}"
    type="button"
    data-banner=${e}
    @click=${i}
  >
    ${n}
  </button>`,$n=(n,i,e,t,r)=>a`<span class="body" data-banner-question>${i}</span>
    <span class="links">
      ${re(e,t,"confirm",!0)}
      ${re(n.t("panel.common.action.cancel"),r,"keep")}
    </span>`,Sn=(n,i,e,t)=>{let r=i.measuring;if(!r)return d;let o=i.session!==null,s=o?n.t("panel.banner.measuring.panel_body",{cover:r.name}):e.service?n.t("panel.wizard.busy.service"):n.t("panel.banner.measuring.body",{cover:r.name});return a`<div
    class="measuring"
    role="status"
    aria-live="polite"
    data-banner-measuring
    ?data-banner-service=${!o&&e.service}
  >
    <strong>${n.t("panel.banner.measuring.title")}</strong>
    ${e.ask==="end_panel"?$n(n,n.t("panel.banner.measuring.end_panel_confirm",{cover:r.name}),n.t("panel.banner.measuring.action.stop"),t.endPanel,()=>t.ask(null)):e.ask==="end_other"?$n(n,n.t("panel.wizard.busy.end_other_confirm"),n.t("panel.wizard.busy.end_other"),t.endOther,()=>t.ask(null)):a`<span class="body">${s}</span>
            <span class="links">
              ${o?a`${re(n.t("panel.banner.measuring.action.resume"),t.resume,"resume")}${re(n.t("panel.banner.measuring.action.stop"),()=>t.ask("end_panel"),"end-panel")}`:e.service?d:a`${re(n.t("panel.common.action.configure"),l=>t.openFlow(l.currentTarget),"configure")}${re(n.t("panel.wizard.busy.end_other"),()=>t.ask("end_other"),"end-other")}`}
            </span>`}
  </div>`};var Rn={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},En=n=>(...i)=>({_$litDirective$:n,values:i}),Ve=class{constructor(i){}get _$AU(){return this._$AM._$AU}_$AT(i,e,t){this._$Ct=i,this._$AM=e,this._$Ci=t}_$AS(i,e){return this.update(i,e)}update(i,e){return this.render(...e)}};var Tn="important",oo=" !"+Tn,Ye=En(class extends Ve{constructor(n){if(super(n),n.type!==Rn.ATTRIBUTE||n.name!=="style"||n.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(n){return Object.keys(n).reduce((i,e)=>{let t=n[e];return t==null?i:i+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${t};`},"")}update(n,[i]){let{style:e}=n.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(i)),this.render(i);for(let t of this.ft)i[t]==null&&(this.ft.delete(t),t.includes("-")?e.removeProperty(t):e[t]=null);for(let t in i){let r=i[t];if(r!=null){this.ft.add(t);let o=typeof r=="string"&&r.endsWith(oo);t.includes("-")||o?e.setProperty(t,o?r.slice(0,-11):r,o?Tn:""):e[t]=r}}return z}});var Xe=m`.sk{--sk-base: var(--myhome-background-soft)}.sk-bar{height:12px;border-radius:6px;background:linear-gradient(90deg,var(--sk-base) 25%,var(--myhome-card) 50%,var(--sk-base) 75%);background-size:400% 100%;animation:sk-slide 1.4s linear infinite}@keyframes sk-slide{0%{background-position:100% 0}to{background-position:0 0}}.sk-intro{max-width:72ch;margin:8px 0 16px;display:flex;flex-direction:column;gap:8px}.sk-controls{display:flex;gap:12px;margin:0 0 16px}.sk-controls .sk-bar{height:44px;border-radius:8px}.sk-groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.sk-groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(300px,1fr);align-items:start}}.sk-group{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.sk-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider);display:flex;flex-direction:column;gap:8px}.sk-body{padding:8px;display:flex;flex-direction:column;gap:2px}.sk-row{min-height:48px;padding:8px;display:flex;flex-direction:column;gap:8px;justify-content:center}.sk-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:0 0 16px;max-width:720px;display:flex;flex-direction:column;gap:12px}`,g=(n,i)=>a`<div
    class="sk-bar"
    aria-hidden="true"
    style=${Ye(i?{width:n,height:i}:{width:n})}
  ></div>`,Gt=()=>a`<div class="sk-row">${g("62%")}${g("40%","10px")}${g("28%","18px")}</div>`,Cn=()=>a`<div class="sk-group">
    <div class="sk-head">${g("45%","16px")}${g("80%","10px")}${g("60%","10px")}</div>
    <div class="sk-body">${Gt()}${Gt()}${Gt()}</div>
  </div>`,An=n=>a`<div class="sk" role="status" aria-busy="true" aria-label=${n.t("panel.common.loading")}>
    <div class="sk-intro">${g("92%","14px")}${g("74%","14px")}${g("36%","12px")}</div>
    <div class="sk-controls">${g("300px")}${g("160px")}</div>
    <div class="sk-groups">${Cn()}${Cn()}</div>
  </div>`,Ze=n=>a`<div class="sk" role="status" aria-busy="true" aria-label=${n.t("panel.common.loading")}>
    <div class="sk-card">
      ${g("40%","16px")}${g("70%","10px")}${g("100%")}${g("100%")}${g("55%")}
    </div>
    <div class="sk-card">${g("35%","16px")}${g("100%","44px")}${g("100%","44px")}</div>
  </div>`;var Qe=m`.strip{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translate(-50%);max-width:92vw;box-sizing:border-box;box-shadow:var(--myhome-shadow)}.strip.drop-zone{z-index:45;padding:14px 28px;min-height:48px;display:flex;align-items:center;border-radius:24px;font-size:14px;font-weight:500;border:2px dashed var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text-soft)}.strip.drop-zone.over{border:2px solid var(--myhome-primary-ink);color:var(--myhome-primary-ink)}.strip.dark{background:var(--myhome-text);color:var(--myhome-background);border-radius:8px;font-size:14px}.strip.armed{z-index:40;padding:10px 16px;display:flex;gap:16px;align-items:center;width:max-content}.strip.armed .what{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;min-width:0}.strip.applying{z-index:70;padding:12px 20px}.strip.applying .under{display:block;font-size:12px;opacity:.75;margin-top:2px}.strip.snack{z-index:70;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:8px}.strip.dark button{min-height:44px;padding:0 12px;border:none;background:transparent;color:var(--myhome-snack-action);font:inherit;font-weight:500;cursor:pointer}.pending-bar{z-index:30;background:var(--myhome-card);border:1px solid var(--myhome-divider);border-radius:28px;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.pending-bar .count{font-size:14px}.pending-bar .locked{font-size:13px;color:var(--myhome-warning-ink);flex-basis:100%}.pending-bar button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.pending-bar .discard{padding:0 12px;background:transparent;color:var(--myhome-text-soft)}.pending-bar .review{padding:0 20px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.pending-bar button[disabled]{color:var(--myhome-text-off);background:var(--myhome-background-soft);cursor:default}@media(max-width:599px){.strip.pending-bar{left:8px;right:8px;transform:none;max-width:none;justify-content:space-between}.strip.pending-bar .count{flex-basis:100%}}`,Pn=(n,i)=>a`<div class="strip drop-zone ${i?"over":""}" data-group="none">
    ${n.t("panel.assign.drop_zone")}
  </div>`,zn=(n,i,e)=>a`<div class="strip dark armed" role="status">
    <span class="what" title=${i}>${n.t("panel.assign.armed",{cover:i})}</span>
    <button type="button" @click=${e}>${n.t("panel.common.action.cancel")}</button>
  </div>`,In=n=>{let{i18n:i}=n;return a`<div class="strip pending-bar">
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
        >`:d}
  </div>`},Je=n=>a`<div class="strip dark applying" role="status">
    ${n.t("panel.banner.applying.title")}
    <span class="under">${n.t("panel.banner.applying.body")}</span>
  </div>`,et=(n,i,e)=>a`<div class="strip dark snack" role="status">
    <span>${i}</span>
    ${e?a`<button type="button" @click=${e}>
          ${n.t("panel.toast.action.undo")}
        </button>`:d}
  </div>`;var Mn=n=>{let i=new Map;for(let e of n.querySelectorAll("[data-row]")){let t=e.getBoundingClientRect();i.set(e.getAttribute("data-row")??"",{top:t.top,left:t.left})}return i},On=(n,i)=>{if(!so())for(let e of n.querySelectorAll("[data-row]")){let t=i.get(e.getAttribute("data-row")??"");if(!t)continue;let r=e.getBoundingClientRect(),o=t.left-r.left,s=t.top-r.top;if(Math.abs(o)<1&&Math.abs(s)<1)continue;e.style.transition="none",e.style.transform=`translate(${o}px, ${s}px)`,e.offsetHeight,e.style.transition="transform 220ms ease",e.style.transform="";let l=()=>{e.style.transition="",e.removeEventListener("transitionend",l)};e.addEventListener("transitionend",l)}},so=()=>typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches;var tt=class{constructor(i){this._start=null;this._longPress=null;this._pressedAt=null;this._ghost=null;this._target=null;this._scroll=null;this._edge=0;this._scroller=null;this._clearLongPressOnce=()=>this._clearLongPress();this._onPressMove=i=>{let e=this._pressedAt;e&&Math.hypot(i.clientX-e.x,i.clientY-e.y)<12||this._clearLongPress()};this._onMove=i=>{let e=this._start;if(!e)return;if(!e.live){if(Math.hypot(i.clientX-e.x,i.clientY-e.y)<6)return;e.live=!0,this._callbacks.onStart(e.cover)}this._moveGhost(i.clientX,i.clientY),this._autoScroll(i.clientX,i.clientY);let t=this._targetAt(i.clientX,i.clientY,e.cover);ao(t,this._target)||(this._target=t,this._callbacks.onOver(t))};this._onUp=()=>this._finish(!0);this._onCancel=()=>this._finish(!1);this._callbacks=i}get dragging(){return this._start?.live?this._start.cover:null}press(i,e){if(!this._callbacks.blocked()){if(this._callbacks.narrow()){this._arm(i,e);return}e.preventDefault(),this._start={cover:i,x:e.clientX,y:e.clientY,live:!1},window.addEventListener("pointermove",this._onMove),window.addEventListener("pointerup",this._onUp),window.addEventListener("pointercancel",this._onCancel),window.addEventListener("blur",this._onCancel)}}arm(i,e){this._callbacks.blocked()||this._arm(i,e)}cancel(){if(this._start?.live){this._finish(!1);return}this._clear()}stop(){this._clear(),this._clearLongPress()}_arm(i,e){this._clearLongPress(),this._pressedAt=e?{x:e.clientX,y:e.clientY}:null,this._longPress=setTimeout(()=>{this._longPress=null,this._callbacks.onArm(i)},450),window.addEventListener("pointerup",this._clearLongPressOnce),window.addEventListener("pointermove",this._onPressMove),window.addEventListener("pointercancel",this._clearLongPressOnce),window.addEventListener("blur",this._clearLongPressOnce)}_clearLongPress(){this._longPress&&(clearTimeout(this._longPress),this._longPress=null),this._pressedAt=null,window.removeEventListener("pointerup",this._clearLongPressOnce),window.removeEventListener("pointermove",this._onPressMove),window.removeEventListener("pointercancel",this._clearLongPressOnce),window.removeEventListener("blur",this._clearLongPressOnce)}_finish(i){let e=this._start?.live??!1;this._clear(),e&&this._callbacks.onEnd(i)}_clear(){window.removeEventListener("pointermove",this._onMove),window.removeEventListener("pointerup",this._onUp),window.removeEventListener("pointercancel",this._onCancel),window.removeEventListener("blur",this._onCancel),this._start=null,this._target=null,this._stopScrolling(),this._ghost?.remove(),this._ghost=null}ghost(i,e){let t=document.createElement("div");t.className="drag-ghost",t.setAttribute("aria-hidden","true"),t.textContent=i,e.appendChild(t),this._ghost=t}_moveGhost(i,e){this._ghost&&(this._ghost.style.transform=`translate(${i+12}px, ${e+8}px)`)}_autoScroll(i,e){let t=this._callbacks.root().querySelector(".groups");if(!t||t.scrollWidth<=t.clientWidth){this._stopScrolling();return}let r=t.getBoundingClientRect(),o=i<r.left+64?-1:i>r.right-64?1:0;if(this._edge=o,this._scroller=t,o===0){this._stopScrolling();return}if(this._scroll===null){let s=()=>{this._edge===0||!this._scroller||(this._scroller.scrollLeft+=this._edge*14,this._scroll=requestAnimationFrame(s))};this._scroll=requestAnimationFrame(s)}}_stopScrolling(){this._edge=0,this._scroll!==null&&(cancelAnimationFrame(this._scroll),this._scroll=null)}_targetAt(i,e,t){let r=this._callbacks.root().elementFromPoint(i,e),o=r?.closest?.("[data-group]");if(!o)return null;let s=o.getAttribute("data-group")??"",l=r?.closest?.("[data-row]"),c=l?.getAttribute("data-row")??null;if(!l||!c||c===t)return{group:s,beforeId:null,afterId:null,end:!0};let p=l.getBoundingClientRect();return e<p.top+p.height/2?{group:s,beforeId:c,afterId:null,end:!1}:{group:s,beforeId:null,afterId:c,end:!1}}},ao=(n,i)=>n===null||i===null?n===i:n.group===i.group&&n.beforeId===i.beforeId&&n.afterId===i.afterId;var it=m`.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;background:var(--myhome-background-soft);color:var(--myhome-text-soft-ink)}.chip.measured{background:var(--myhome-primary-pastel);color:var(--myhome-text);box-shadow:inset 0 0 0 1px var(--myhome-primary)}.chip.adjusted{background:var(--myhome-accent-pastel);color:var(--myhome-text)}.chip .dot{width:6px;height:6px;border-radius:3px;background:var(--myhome-accent);display:inline-block}`,nt=(n,i,e,t)=>{let r=i==="measured"?"measured":i==="adjusted"?"adjusted":"neutral",o;return t&&i==="inherited"?o=n.t("panel.overview.cover.origin_inherited"):t&&i==="adjusted"?o=n.t("panel.overview.cover.origin_adjusted"):o=n.origin(i,e),a`<span class="chip ${r}"
    >${r==="adjusted"?a`<span class="dot" aria-hidden="true"></span>`:d}${o}</span
  >`};var Ln=m`.row{position:relative;display:flex;align-items:flex-start;gap:8px;padding:8px;border-radius:8px;min-height:48px;-webkit-user-select:none;-webkit-touch-callout:none}.row .divider{position:absolute;left:8px;right:8px;top:-1px;height:1px;background:var(--myhome-divider);opacity:.6;pointer-events:none}.row .insert-line{position:absolute;left:8px;right:8px;top:-2px;height:3px;border-radius:2px;background:var(--myhome-primary-ink);pointer-events:none}.row .pending-outline{position:absolute;inset:0;border:2px dashed var(--myhome-primary-ink);border-radius:8px;pointer-events:none}.row .source-veil{position:absolute;inset:0;background:var(--myhome-background-soft);opacity:.7;border-radius:8px;pointer-events:none}.row .handle{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);cursor:grab;font-size:18px;letter-spacing:2px;border-radius:8px;touch-action:none;-webkit-user-select:none;user-select:none}.row .handle[disabled]{cursor:default;color:var(--myhome-text-off)}@media(max-width:599px){.row .handle{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.row .handle:focus-visible{position:static;width:48px;height:48px;margin:0;overflow:visible;clip-path:none}}.row .body{flex:1 1 auto;min-width:0}.row .main{display:block;width:100%;text-align:left;border:none;background:transparent;color:inherit;font:inherit;cursor:pointer;padding:2px 0;border-radius:6px}.row .name{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:14.5px;line-height:1.35}.row .sub{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.row .chips:empty{display:none}.row .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}.row .warn{display:block;font-size:12.5px;color:var(--myhome-warning-ink);margin-top:4px}.route{display:inline-flex;align-items:center;gap:2px;font-size:12px;color:var(--myhome-primary-ink);background:var(--myhome-primary-faint);border:1px dashed var(--myhome-primary-ink);border-radius:10px;padding:2px 2px 2px 8px;max-width:100%}.route .text{min-width:0;overflow-wrap:anywhere}.route .withdraw{width:48px;height:48px;margin:-14px -14px -14px 0;display:inline-flex;align-items:center;justify-content:center;border:none;background:transparent;color:inherit;font:inherit;font-size:14px;line-height:1;cursor:pointer;border-radius:24px}.row .note{display:block;font-size:12.5px;color:var(--myhome-info-ink);margin-top:4px}`,jt=(n,i,e)=>{let t=i.height!==null?n.t("panel.overview.cover.travel",{travel:n.number(i.height,0)}):e?n.t("panel.overview.cover.travel_needed"):n.t("panel.overview.cover.travel_unknown");return i.area?`${i.area} · ${t}`:t},lo=(n,i)=>i.has_own.length===0?"":M.every(e=>i.has_own.includes(e))?n.t("panel.assign.pending.all_own"):n.t("panel.assign.pending.some_own"),Dn=(n,i)=>{let{i18n:e,pending:t}=i,r=!!t&&t.to!==null&&n.height===null,o=t?lo(e,n):"",s=`chips-${n.unique_id}`;return a`<div class="row" data-row=${n.unique_id}>
    ${i.insertBefore?a`<div class="insert-line" aria-hidden="true"></div>`:i.first?d:a`<div class="divider" aria-hidden="true"></div>`}
    ${t?a`<div class="pending-outline" aria-hidden="true"></div>`:d}
    ${i.dragging?a`<div class="source-veil" aria-hidden="true"></div>`:d}
    <button
      class="handle"
      type="button"
      ?disabled=${i.locked}
      aria-label=${e.t("panel.assign.handle",{cover:n.name})}
      title=${i.locked?e.t("panel.banner.measuring.title"):e.t("panel.assign.handle_hint")}
      @pointerdown=${l=>i.onGrab(n,l)}
      @click=${l=>l.stopPropagation()}
      @keydown=${l=>{(l.key==="Enter"||l.key===" ")&&(l.preventDefault(),i.locked||i.onPick(n))}}
    >
      ⠿
    </button>
    <div
      class="body"
      @pointerdown=${l=>i.onRowPress(n,l)}
    >
      <button class="main" type="button" title=${n.name} aria-describedby=${s}
        @click=${()=>i.onOpen(n)}>
        <span class="name">${n.name}</span>
        <span class="sub">${jt(e,n,r)}</span>
        ${o?a`<span class="note">${o}</span>`:d}
        ${n.profile_missing?a`<span class="warn"
              >${e.t("panel.overview.cover.profile_missing",{profile:n.profile??""})}</span
            >`:d}
      </button>
      <div class="chips" id=${s}>
        ${nt(e,n.origin,n.profile,i.short)}
        ${t?a`<span class="route">
              <span class="text">${i.route}</span>
              <button
                class="withdraw"
                type="button"
                aria-label=${e.t("panel.assign.action.withdraw")}
                title=${e.t("panel.assign.action.withdraw")}
                @pointerdown=${l=>l.stopPropagation()}
                @click=${()=>i.onWithdraw(n)}
              >
                ✕
              </button>
            </span>`:d}
      </div>
    </div>
  </div>`};var Hn=m`.backdrop{position:fixed;inset:0;background:#0006;z-index:60}.dialog{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(440px,92vw);max-height:80vh;overflow:auto;background:var(--myhome-card);color:var(--myhome-text);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);z-index:61;padding:20px;box-sizing:border-box}.dialog h2{margin:0 0 4px;font-size:18px;font-weight:500}.dialog .subtitle{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft)}.dialog .options{display:flex;flex-direction:column;gap:8px}.dialog .option{text-align:left;border-radius:8px;font:inherit;padding:12px;min-height:48px;cursor:pointer;border:1px solid var(--myhome-field-border);background:transparent;color:inherit}.dialog .option.current{border-color:var(--myhome-primary-ink);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.dialog .option .line{display:flex;align-items:baseline;gap:8px}.dialog .option .title{font-weight:500;flex:1}.dialog .option .tag{font-size:12.5px;color:var(--myhome-primary-ink)}.dialog .option .meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.dialog .foot{display:flex;justify-content:flex-end;margin-top:12px}.dialog .foot button{min-height:44px;padding:0 16px;border:none;background:transparent;color:var(--myhome-text-soft);font:inherit;font-size:14px;cursor:pointer}`,co=(n,i)=>i.missing||i.values.opening_time===void 0?n.t("panel.overview.group.values_unknown"):n.t("panel.dialog.option.profile_meta",{travel:i.reference_height===null?"?":n.number(i.reference_height,0),opening:n.number(i.values.opening_time,1),closing:n.number(i.values.closing_time,1)}),Fn=n=>{let{i18n:i}=n,e=(t,r,o)=>a`<button
    class="option ${n.current===t?"current":""}"
    type="button"
    aria-current=${n.current===t?"true":d}
    @click=${()=>n.onPick(t)}
  >
    <span class="line"
      ><span class="title">${r}</span
      >${n.current===t?a`<span class="tag">${i.t("panel.dialog.option.current")}</span>`:d}</span
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
        ${n.profiles.map(t=>e(t.name,i.t("panel.dialog.option.profile",{profile:t.name}),co(i,t)))}
        ${e(null,i.t("panel.dialog.option.none"),i.t("panel.dialog.option.none_meta"))}
      </div>
      <div class="foot">
        <button type="button" @click=${n.onClose}>
          ${i.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `};var Nn=m`.groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(260px,1fr);gap:16px;align-items:start;overflow-x:auto;padding:4px 0 8px;scroll-padding-inline:4px;scrollbar-width:thin;scrollbar-color:var(--myhome-field-border) transparent;overscroll-behavior-x:contain}.groups::-webkit-scrollbar{height:8px}.groups::-webkit-scrollbar-thumb{background:var(--myhome-field-border);border-radius:4px}.groups::-webkit-scrollbar-track{background:transparent}}.group{position:relative;background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.group-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider)}.group-head .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.group-head h2{margin:0;font-size:19px;font-weight:700;flex:1 1 auto;min-width:0}.group-head h2 button{border:none;background:transparent;color:var(--myhome-primary);font:inherit;cursor:pointer;padding:0;min-height:28px;text-align:left}.group-head .count{color:var(--myhome-text-soft);font-size:13px}.group-head .meta{margin:6px 0 0;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}.group-head .meta.second{margin-top:4px}.group-head .meta.warn{color:var(--myhome-warning-ink)}.group-body{display:flex;flex-direction:column;padding:8px;gap:2px;min-height:56px}.group-body .empty{margin:8px;font-size:13px;color:var(--myhome-text-soft)}.group-body .insert-end{margin:0 8px;height:3px;border-radius:2px;background:var(--myhome-primary-ink);pointer-events:none}.group .over,.group .armed-target{position:absolute;inset:0;border-radius:var(--myhome-radius);pointer-events:none}.group .over{border:2px solid var(--myhome-primary-ink)}.group .armed-target{border:2px dashed var(--myhome-primary-ink)}.group.collapsed .group-head{border-bottom:none;min-height:48px;cursor:pointer}`,Vt=n=>n===null?"none":`profile:${n}`,Wn=n=>n==="none"?null:n.slice(8),qn=(n,i)=>{let{i18n:e}=i,t=n.covers.length===1?e.t("panel.overview.group.count_one"):e.t("panel.overview.group.count",{count:n.covers.length}),r=i.collapsed;return a`<section
    class="group ${r?"collapsed":""}"
    data-group=${Vt(n.key)}
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
      ${n.values&&!r?a`<p class="meta">${n.values}</p>`:d}
      ${r?d:n.warning?a`<p class="meta second warn">${n.warning}</p>`:n.provenance?a`<p class="meta second">${n.provenance}</p>`:d}
    </div>
    ${r?d:a`<div class="group-body">
          ${n.covers.map((o,s)=>Dn(o,{i18n:e,short:o.profile===n.key,first:s===0,pending:i.pending.find(l=>l.cover===o.unique_id),route:i.route(o),locked:i.locked,insertBefore:i.insertBefore===o.unique_id,dragging:i.dragging===o.unique_id,onOpen:i.onOpenCover,onGrab:i.onGrab,onRowPress:i.onRowPress,onPick:i.onPick,onWithdraw:i.onWithdraw}))}
          ${i.insertEnd?a`<div class="insert-end" aria-hidden="true"></div>`:d}
          ${n.covers.length===0?a`<p class="empty">${e.t("panel.overview.group.empty")}</p>`:d}
        </div>`}
    ${i.over?a`<div class="over" aria-hidden="true"></div>`:d}
    ${r?a`<div class="armed-target" aria-hidden="true"></div>`:d}
  </section>`};var Un=[je,m`.sheet .body[aria-busy=true] table,.sheet .body[aria-busy=true] .note{opacity:.55;transition:opacity .12s ease}.sheet .intro{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .travel-note{background:var(--myhome-info-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}.sheet .travel-note strong{font-weight:500;display:block;margin-bottom:4px}.sheet .item{border:1px solid var(--myhome-divider);border-radius:8px;padding:12px;margin:0 0 12px}.sheet .item .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.sheet .item .name{font-weight:500;flex:1 1 auto;min-width:0}.sheet .item .item-route{font-size:13px;color:var(--myhome-text-soft)}.sheet label.travel{display:flex;align-items:center;gap:8px;margin:10px 0 2px;font-size:13.5px}.sheet label.travel .what{flex:1}.sheet label.travel input{width:96px;height:44px;border-radius:8px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:inherit;padding:0 10px;font:inherit;font-size:14px;text-align:right}.sheet label.travel input[aria-invalid=true]{border-color:var(--myhome-error-ink)}.sheet .field-error{margin:2px 0 0;font-size:12.5px;color:var(--myhome-error-ink);text-align:right}.sheet table{width:100%;border-collapse:collapse;margin:10px 0 0;font-size:13.5px}.sheet th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}.sheet th.what{text-align:left}.sheet th.after{font-weight:500;color:var(--myhome-text)}.sheet td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}.sheet td.what{text-align:left;color:var(--myhome-text-soft)}.sheet td.after{font-weight:500}.sheet .note{margin:10px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .problem{margin:10px 0 0;font-size:12.5px;color:var(--myhome-error-ink);line-height:1.5}.sheet .show-all{border:none;background:transparent;color:var(--myhome-primary-ink);font:inherit;font-size:13.5px;cursor:pointer;padding:4px 0;min-height:44px}.sheet .refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 12px;font-size:13.5px;line-height:1.5}.sheet .foot{padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));border-top:1px solid var(--myhome-divider);display:flex;gap:12px;justify-content:flex-end}.sheet .foot button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.sheet .foot .back{padding:0 16px;background:transparent;color:var(--myhome-text-soft)}.sheet .foot .confirm{padding:0 24px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.sheet .foot .confirm[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}`],po=(n,i,e,t,r)=>{if(M.every(s=>i.has_own.includes(s)))return n.t("panel.review.note.all_own");if(i.has_own.length>0)return n.t("panel.review.note.some_own");if(e.to===null)return t?.origin==="from_the_file"?n.t("panel.review.note.back_to_file"):n.t("panel.review.note.back_to_defaults");let o=r.get(e.to);return!t||t.height===null||!o||o.reference_height===null?"":n.t("panel.review.note.scaled",{profile:e.to,reference:n.number(o.reference_height,0),travel:n.number(t.height,0)})},Bn=(n,i,e,t)=>n.refusal(e,{cover:i.name,covers:i.name,count:1,profile:t.to??"",key:n.t("panel.review.travel.label"),min:20,max:500}),Kn=n=>{let{i18n:i}=n,e=new Map((n.preview??[]).map(c=>[c.cover_unique_id,c])),t=n.pending.map(c=>({change:c,cover:n.covers.get(c.cover)})).filter(c=>c.cover!==void 0),r=t.filter(({change:c,cover:p})=>c.to!==null&&p.height===null&&ve(n.heights[c.cover])!==null).length,o=n.showAll?[...fe,...ge]:fe,s=c=>F(i.t(`options.step.calibration_edit.data.${c}`)),l=(c,p)=>{let u=ee[c];return j(i.number(p,O[c]??1),u?i.t(u):"")};return a`
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
        ${n.refusal?a`<div class="refusal" role="alert">${n.refusal}</div>`:d}
        ${r>0?a`<div class="travel-note">
              <strong>${i.t("panel.review.travel.title")}</strong>
              ${i.t("panel.review.travel.hint")}
            </div>`:d}
        ${t.map(({change:c,cover:p})=>{let u=e.get(c.cover),h=n.heights[c.cover],v=c.to!==null&&p.height===null,_=v?ve(h):null,E=_!==null&&(n.forced||(h??"")!==""),X=u&&u.problem===null?o.filter(f=>u.values[f]!==void 0&&p.values[f]!==void 0):[];return a`<section class="item">
            <div class="line">
              <span class="name">${p.name}</span>
              <span class="item-route">${n.route(p)}</span>
            </div>
            ${v?a`<label class="travel">
                    <span class="what">${i.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${h??""}
                      ?disabled=${n.applying}
                      aria-label=${i.t("panel.review.travel.aria")}
                      aria-invalid=${E?"true":"false"}
                      placeholder=${i.t("panel.review.travel.placeholder")}
                      @input=${f=>n.onHeight(c.cover,f.target.value)}
                    />
                    <span>${i.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${E?a`<p class="field-error">
                        ${_==="missing_travel"?i.t("panel.review.travel.required"):Bn(i,p,_,c)}
                      </p>`:d}`:d}
            ${u&&u.problem!==null&&u.problem!=="missing_travel"?a`<p class="problem">
                  ${Bn(i,p,u.problem,c)}
                </p>`:d}
            ${X.length>0?a`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${i.t("panel.review.before")}</th>
                      <th class="after">${i.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${X.map(f=>a`<tr>
                        <td class="what">${s(f)}</td>
                        <td>${l(f,p.values[f])}</td>
                        <td class="after">${l(f,u.values[f])}</td>
                      </tr>`)}
                  </tbody>
                </table>`:d}
            ${(()=>{let f=po(i,p,c,u,n.profiles);return f?a`<p class="note">${f}</p>`:d})()}
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
  `};var rt=class extends w{constructor(){super();this._trap=new q;this._returnTo=null;this._returnToRow=null;this._onKey=e=>{if(e.key==="Escape"){if(this.state.drag){this._drag.cancel();return}if(this.state.armed){this.actions.arm(null);return}if(this.state.dialog){this.actions.dialog(null);return}this.state.review&&!this.state.applying&&this.actions.review(!1)}};this._flip=null;this._narrowQuery=typeof matchMedia=="function"?matchMedia("(max-width: 599px)"):null;this._onWidth=()=>this.requestUpdate();this._route=e=>{let t=Le(e.unique_id,this.state.pending);return t?Xi(this.i18n,e.profile??null,t.to):""};this._onGrab=(e,t)=>{this._drag.press(e.unique_id,t)};this._onRowPress=(e,t)=>{this._narrow&&!this._locked&&this._drag.arm(e.unique_id,t)};this.i18n=new y,this.state=Y({view:"overview",params:{},path:"/"}),this.actions={},this._drag=new tt({root:()=>this.renderRoot,blocked:()=>this._locked,narrow:()=>this._narrow,onArm:e=>{let t=this._cover(e);t&&this.actions.arm(t)},onStart:e=>{let t=this._cover(e);t&&(this._drag.ghost(t.name,this.renderRoot),this.actions.drag(t))},onOver:e=>this.actions.over(e),onEnd:e=>this._endDrag(e)})}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[$,k,S,W,it,Ln,Nn,Qe,Hn,Un,m`:host{display:block;background:transparent}.intro{margin:8px 0 4px;max-width:72ch}.intro p{margin:0 0 8px;line-height:1.55}.counts{margin:0 0 16px;color:var(--myhome-text-soft)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.controls .search{flex:1 1 220px;max-width:340px}.controls .spacer{flex:1 1 auto}.select-wrap{position:relative;display:inline-flex}.select-wrap:after{content:"";position:absolute;right:13px;top:50%;width:7px;height:7px;border-right:1.6px solid var(--myhome-text-soft);border-bottom:1.6px solid var(--myhome-text-soft);border-radius:1px;transform:translateY(-70%) rotate(45deg);pointer-events:none}select.field{appearance:none;padding-right:36px}a.cta{display:inline-flex;align-items:center;text-decoration:none}.welcome{max-width:640px;margin:48px auto;padding:32px}.welcome h2{margin:0 0 12px;font-size:22px;font-weight:500}.welcome p{margin:0 0 8px;line-height:1.55}.welcome .soft{color:var(--myhome-text-soft);margin-bottom:24px}.welcome .after{margin:12px 0 0;font-size:13px;color:var(--myhome-text-soft)}.notice{padding:16px;margin:16px 0;font-size:14px;line-height:1.55}.notice .actions{margin-top:12px}.groups{margin-bottom:96px}.groups.targeting{margin-bottom:120px}.drag-ghost{position:fixed;left:0;top:0;z-index:80;pointer-events:none;background:var(--myhome-card);color:var(--myhome-text);border:1px solid var(--myhome-primary-ink);border-radius:8px;box-shadow:var(--myhome-shadow);padding:10px 14px;font-size:14px;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}`]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey),this._narrowQuery?.addEventListener("change",this._onWidth)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._narrowQuery?.removeEventListener("change",this._onWidth),this._drag.stop(),this._trap.release()}updated(e){if(this._locked){let t=this._drag.dragging!==null;this._drag.stop(),t&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"))}if(e.has("state")){let t=e.get("state");if(this._manageFocus(t),this._flip){let r=this._flip;this._flip=null,requestAnimationFrame(()=>On(this.renderRoot,r))}}}_beforeMove(){this._flip=Mn(this.renderRoot)}_manageFocus(e){let t=this.state.dialog!==null||this.state.review,r=(e?.dialog??null)!==null||(e?.review??!1);if(t&&!r){let o=this._activeElement();this._returnTo=o,this._returnToRow=o?.closest("[data-row]")?.getAttribute("data-row")??null,requestAnimationFrame(()=>{let s=this.renderRoot.querySelector("[data-focus-root]");s&&this._trap.hold(s)});return}if(!t&&r){this._trap.release();let o=this._returnTo,s=this._returnToRow;this._returnTo=null,this._returnToRow=null,requestAnimationFrame(()=>{((s?[...this.renderRoot.querySelectorAll("[data-row]")].find(p=>p.getAttribute("data-row")===s)?.querySelector(".handle"):null)??(o?.isConnected?o:null))?.focus()})}}_activeElement(){let e=this.renderRoot.activeElement;return e instanceof HTMLElement?e:null}get _overview(){return this.state.overview}get _locked(){return this._overview?.measuring!=null||this.state.applying}get _narrow(){return this._narrowQuery?.matches??!1}_cover(e){return this._overview?.covers.find(t=>t.unique_id===e)}get _covers(){let e=this._overview;return e?Qi(e,this.state.order):[]}get _rooms(){let e=new Set;for(let t of this._overview?.covers??[])t.area&&e.add(t.area);return Array.from(e).sort((t,r)=>t.localeCompare(r,this.i18n.language))}_matches(e){let t=this.state.search.trim().toLowerCase();return t&&!e.name.toLowerCase().includes(t)?!1:!this.state.room||e.area===this.state.room}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group.values_unknown"):this.i18n.t("panel.overview.group.values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),opening:this.i18n.number(e.values.opening_time,1),closing:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml"||(this._overview?.covers??[]).some(l=>l.profile===e.name&&l.profile_from_file))return this.i18n.t("panel.overview.group.from_file");if(!e.measured_on)return this.i18n.t("panel.overview.group.provenance_missing");let r=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.group.measured_on_gone",{date:r});let o=this.i18n.t("panel.overview.group.measured_on",{cover:e.measured_on_name,date:r}),s=(this._overview?.covers??[]).find(l=>l.unique_id===e.measured_on);if(s&&s.profile!==e.name){let l=s.profile??this.i18n.t("panel.overview.group.no_profile");o+=` · ${this.i18n.t("panel.profile.provenance_now_profile",{profile:l})}`}return o}get _groups(){let e=this._overview;if(!e)return[];let t=this._covers,r=s=>t.filter(l=>Oe(l,this.state.pending)===s&&this._matches(l)),o=e.profiles.map((s,l)=>({key:s.name,id:`group-${l}`,title:this.i18n.t("panel.overview.group.profile",{profile:s.name}),values:this._valuesLine(s),provenance:this._provenanceLine(s),warning:s.missing?this.i18n.t("panel.overview.group.missing"):"",covers:r(s.name)}));return o.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group.no_profile"),values:this.i18n.t("panel.overview.group.no_profile_note"),provenance:"",warning:"",covers:r(null)}),o}_appendAtEnd(e,t){if(this.state.order===null||t===(e.profile??null))return;let r=this._covers;this.actions.setOrder(Ji(r.map(o=>o.unique_id),e.unique_id,r.filter(o=>Oe(o,this.state.pending)===t).map(o=>o.unique_id)))}_endDrag(e){let t=this.state,r=t.drag,o=r?.insert??null,s=r?.over??null,l=r?this._cover(r.cover):void 0;if(this.actions.drag(null),!e||!l||s===null){r&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));return}let c=Wn(s),p=this._covers.map(_=>_.unique_id),u=Rt(p,l.unique_id,o??{beforeId:null,afterId:null});this._beforeMove();let h=Le(l.unique_id,t.pending),v=h?h.to:l.profile??null;if(c!==v){this.actions.setOrder(u),this.actions.assign(l,c);return}if(t.pending.length>0){this.actions.setOrder(u),this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));return}this.actions.reorder(u)}_renderControls(){return a`<div class="controls">
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
      <!--
        The guided calibration, in this panel (SPEC §6). It used to be a link to the
        integration page, where the user still had to find "Configura"; it is a button now
        because what it does is move between two screens of this panel, and it carries no
        shutter - the wizard asks which one.
      -->
      <button
        class="cta secondary compact"
        type="button"
        @click=${()=>this.actions.calibrate(null)}
      >
        ${this.i18n.t("panel.firstrun.action.measure")}
      </button>
    </div>`}_renderFirstRun(){return a`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <button class="cta" type="button" @click=${()=>this.actions.calibrate(null)}>
        ${this.i18n.t("panel.firstrun.action.measure")}
      </button>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`}_renderStrips(){let e=this.state;if(e.route.view!=="overview")return d;if(e.drag)return Pn(this.i18n,e.drag.over==="none");if(e.armed){let t=this._cover(e.armed);return zn(this.i18n,t?.name??"",()=>this.actions.arm(null))}return e.applying?Je(this.i18n):e.snack?et(this.i18n,e.snack.message,e.snack.undoToken?()=>this.actions.undo():null):e.pending.length>0&&!e.review?In({i18n:this.i18n,count:e.pending.length,locked:this._locked,lockedCover:this._overview?.measuring?.name??"",onDiscard:()=>{this._beforeMove(),this.actions.discardAll()},onReview:()=>this.actions.review(!0)}):d}_renderDialog(){let e=this.state.dialog?this._cover(this.state.dialog):void 0;return e?Fn({i18n:this.i18n,cover:e,profiles:this._overview?.profiles??[],current:Oe(e,this.state.pending),onPick:t=>{this._beforeMove(),this._appendAtEnd(e,t),this.actions.assign(e,t)},onClose:()=>this.actions.dialog(null)}):d}_renderReview(){let e=this._overview;return!this.state.review||!e?d:Kn({i18n:this.i18n,pending:this.state.pending,covers:new Map(e.covers.map(t=>[t.unique_id,t])),profiles:new Map(e.profiles.map(t=>[t.name,t])),preview:this.state.preview,previewing:this.state.previewing,heights:this.state.heights,forced:this.state.heightsForced,showAll:this.state.showAll,applying:this.state.applying,refusal:this.state.writeError?this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{}):"",route:this._route,onHeight:(t,r)=>this.actions.height(t,r),onToggleShowAll:()=>this.actions.toggleShowAll(),onConfirm:()=>this.actions.confirm(),onClose:()=>this.actions.review(!1)})}render(){let e=this._overview;if(!e)return a`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return a`<section class="card welcome">
        <h2>${this.i18n.t("panel.overview.no_basic_covers_title")}</h2>
        <div>${J(this.i18n.t("panel.overview.no_basic_covers"))}</div>
        <a class="cta secondary" href=${N} title=${this.i18n.t("panel.common.opens_configure")}
          >${this.i18n.t("panel.common.action.configure")}</a
        >
      </section>`;if(e.profiles.length===0)return this._renderFirstRun();let t=this._groups,r=t.reduce((l,c)=>l+c.covers.length,0),o=this.state.search.trim()!==""||this.state.room!=="",s=this.state.drag;return a`
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
          </div>`:a`<div class="groups ${this.state.armed!==null?"targeting":""}">
            ${t.map(l=>{let c=Vt(l.key),p=s?.insert??null,u=p!==null&&p.group===c;return qn(l,{i18n:this.i18n,pending:this.state.pending,route:this._route,locked:this._locked,collapsed:this.state.armed!==null,over:s?.over===c,insertBefore:u?p.beforeId:null,insertEnd:u?p.end||p.afterId===l.covers.at(-1)?.unique_id:!1,dragging:s?.cover??null,onOpenProfile:h=>this.actions.openProfile(h),onOpenCover:h=>this.actions.openCover(h.unique_id),onGrab:this._onGrab,onRowPress:this._onRowPress,onPick:h=>this.actions.dialog(h),onWithdraw:h=>{this._beforeMove(),this.actions.withdraw(h)},onTarget:h=>{let v=this.state.armed?this._cover(this.state.armed):void 0;v&&(this._beforeMove(),this._appendAtEnd(v,h),this.actions.assign(v,h))}})})}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",rt);var ot=m`:host{display:block}.card{padding:16px;margin:0 0 16px;max-width:720px}h2{margin:0 0 4px;font-size:16px;font-weight:500}h2:focus-visible{outline:2px solid var(--myhome-primary-ink);outline-offset:4px}.sub{margin:0;font-size:13px;color:var(--myhome-text-soft)}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}.intro{margin:0 0 12px;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}table[aria-busy=true],.rows[aria-busy=true]{opacity:.55;transition:opacity .12s ease}.rows{display:flex;flex-direction:column}.row{display:flex;align-items:baseline;gap:8px;padding:8px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.row .what{flex:1 1 150px;color:var(--myhome-text-soft)}.row .value{font-variant-numeric:tabular-nums;font-weight:500}.row .from{flex-basis:100%;font-size:12px;color:var(--myhome-text-soft);text-align:right}.row .instead{font-size:12px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}h3{margin:16px 0 4px;font-size:14px;font-weight:500}.actions{display:flex;flex-direction:column;gap:8px}.wide{min-height:48px;border:none;border-radius:8px;background:var(--myhome-primary-faint);color:var(--myhome-primary-ink);font:inherit;font-size:14px;cursor:pointer;text-align:left;padding:10px 14px;display:block;width:100%}.wide.destructive{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}.wide[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.wide .note{display:block;color:var(--myhome-text-soft);font-size:12.5px;margin-top:2px}.warn{background:var(--myhome-warning-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13px;line-height:1.5}.warn strong{font-weight:500;display:block;margin-bottom:4px}.caution{background:var(--myhome-warning-pastel);border-left:4px solid var(--myhome-warning-ink);border-radius:0 8px 8px 0;padding:12px 12px 12px 14px;margin:8px 0 2px;font-size:13px;line-height:1.5}.caution strong{display:block;font-size:14px;font-weight:700;margin-bottom:4px}.caution p{margin:0}.danger{background:var(--myhome-error-pastel);border-radius:8px;padding:16px;font-size:14px;line-height:1.55}.danger strong{font-weight:500}.danger p{margin:8px 0 0}.danger ul{margin:4px 0 0;padding:0 0 0 20px;line-height:1.7}.danger .soft{color:var(--myhome-text-soft);font-size:13px}.fields{display:flex;flex-direction:column;gap:10px}label.field-row{display:flex;align-items:center;gap:8px;font-size:13.5px}label.field-row .what{flex:1}label.field-row input{width:110px;text-align:right}label.field-row .unit{color:var(--myhome-text-soft);width:24px}.field[aria-invalid=true]{border-color:var(--myhome-error-ink)}.field-error{margin:2px 26px 0 0;font-size:12.5px;color:var(--myhome-error-ink);text-align:right}.foot{display:flex;gap:12px;justify-content:flex-end;margin-top:16px}table{width:100%;border-collapse:collapse;margin:16px 0 0;font-size:13.5px}th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}th.what,td.what{text-align:left}th.after{font-weight:500;color:var(--myhome-text)}td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}td.what{color:var(--myhome-text-soft)}td.after{font-weight:500}a{color:var(--myhome-primary-ink)}.refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}`,ke=(n,i,e,t,r)=>a`<div class="row">
  <span class="what">${n}</span>
  <span class="value">${i}${e?a` ${e}`:d}</span>
  ${r?a`<span class="instead">${r}</span>`:d}
  ${t?a`<span class="from">${t}</span>`:d}
</div>`,st=(n,i)=>a`<div
  class="caution"
  role="note"
  aria-labelledby="advanced-note-title"
  data-advanced-note
>
  <strong id="advanced-note-title">${n}</strong>
  <p>${i}</p>
</div>`,at=(n,i,e,t,r)=>{let o=n.find(s=>e.includes(i(s)));return n.map(s=>s===o?a`${t()}${r(s)}`:r(s))},Se=n=>a`<div>
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
  ${n.error?a`<p class="field-error">${n.error}</p>`:d}
</div>`,R=n=>a`<button
  class="wide ${n.destructive?"destructive":""}"
  type="button"
  title=${n.title??""}
  data-wide=${n.mark??""}
  ?disabled=${n.disabled??!1}
  @click=${n.onClick}
>
  ${n.label}
  ${n.note?a`<span class="note">${n.note}</span>`:d}
</button>`,A=(n,i,e,t=!1)=>a`<div class="foot">
  <button class="cta text" type="button" ?disabled=${t} @click=${i}>
    ${n}
  </button>
  ${e}
</div>`;var oe=[...fe,...ge],lt=class extends w{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)&&this.state.dialog===null){if(this.state.detail.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new y,this.state=Y({view:"cover",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[$,k,S,W,it,ot,Xe]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.detail,t=`${e.for??""}|${e.mode}`;if(t===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=t,B(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}get _cover(){return this.state.detail.answer?.cover??null}_fullLabel(e){return this.i18n.t(`options.step.calibration_edit.data.${e}`)}_label(e){return F(this._fullLabel(e))}_unit(e){let t=ee[e];return t?this.i18n.t(t):""}_number(e,t){return this.i18n.number(t,O[e]??L[e]?.decimals??1)}_problem(e,t){return this.i18n.refusal(t,{key:this._fullLabel(e),min:L[e]?.min??0,max:L[e]?.max??0,cover:this.state.detail.answer?.cover.name??""})}_destination(){let e=this.state.detail.answer?.forget;return e?e.falls_back_to==="profile"?this.i18n.t("panel.detail.destination.profile",{profile:e.profile??""}):e.falls_back_to==="file"?this.i18n.t("panel.detail.destination.file"):this.i18n.t("panel.detail.destination.defaults"):""}render(){let e=this.state.detail;return e.loading?Ze(this.i18n):e.answer?a`${this._head(e.answer.cover)}
    ${this.state.writeError?a`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:d}
    ${e.mode==="view"?this._view(e.answer.cover,e.answer.keys):d}
    ${e.mode==="edit"?this._edit(e.answer.keys):d}
    ${e.mode==="travel"?this._travel(e.answer.cover):d}
    ${e.mode==="correct"?this._correct():d}
    ${e.mode==="remove"?this._remove(e.answer.cover):d}`:a`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.unknown")}</h2>
        <p class="sub">
          ${e.error?this.i18n.refusal(e.error.translation_key,e.error.translation_placeholders??{}):""}
        </p>
        ${A(this.i18n.t("panel.common.action.retry"),this.actions.retry,a`<button class="cta secondary compact" type="button" @click=${this.actions.back}>
            ${this.i18n.t("panel.common.action.back")}
          </button>`)}
      </div>`}_head(e){let t=[e.area,e.height===null?this.i18n.t("panel.overview.cover.travel_unknown"):this.i18n.t("panel.overview.cover.travel",{travel:this.i18n.number(e.height,0)}),e.profile?this.i18n.t("panel.overview.cover.follows",{profile:e.profile}):null].filter(o=>!!o),r=e.level==="precise"?this.i18n.t("panel.detail.level_thorough"):e.level==="basic"?this.i18n.t("panel.detail.level_basic"):null;return a`<section class="card">
      <p class="sub">${t.join(" · ")}</p>
      <div class="chips">
        ${nt(this.i18n,e.origin,e.profile,!1)}
        ${e.measured_at?a`<span class="chip"
              >${this.i18n.t("panel.detail.measured_at",{date:this.i18n.date(e.measured_at)})}${r?` · ${r}`:""}</span
            >`:d}
        ${e.verify_note!==null?a`<span class="chip"
              >${this.i18n.t("panel.detail.verify_note",{deviation:this.i18n.number(e.verify_note,1)})}</span
            >`:d}
      </div>
      ${e.profile_missing?a`<p class="warn" style="margin-top:12px;margin-bottom:0">
            ${this.i18n.t("panel.overview.cover.profile_missing",{profile:e.profile??""})}
          </p>`:d}
      ${e.profile_from_file?a`<p class="sub" style="margin-top:8px">
            ${this.i18n.t("panel.overview.group.from_file")}
          </p>`:d}
    </section>`}_view(e,t){let r=oe.map(l=>t.find(c=>c.key===l)).filter(l=>l!==void 0),o=e.has_own.length>0,s=o&&e.level!=="precise";return a`<section class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.values.title")}</h2>
        <p class="intro">${this.i18n.t("panel.detail.values.intro")}</p>
        <div class="rows">
          ${r.map(l=>this._valueRow(e,l))}
        </div>
      </section>
      <section class="card actions">
        ${R({label:this.i18n.t("panel.detail.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
        ${R({label:this.i18n.t("panel.detail.action.travel"),note:this.i18n.t("options.step.calibration_edit.data_description.height"),disabled:this._locked,onClick:()=>this.actions.mode("travel")})}
        ${R({label:this.i18n.t("panel.detail.action.assign"),disabled:this._locked,onClick:this.actions.assign})}
        ${e.profile?R({label:this.i18n.t("panel.overview.group.open"),note:this.i18n.t("panel.overview.group.profile",{profile:e.profile}),onClick:()=>this.actions.openProfile(e.profile)}):d}
        ${this._calibrateButton("panel.detail.action.measure_again","panel.detail.action.measure_again_note",{},"measure-again")}
        ${o?R({label:this.i18n.t("panel.detail.action.correct"),note:this.i18n.t("panel.detail.action.correct_note"),mark:"correct",onClick:()=>this.actions.mode("correct")}):d}
        ${s?this._calibrateButton("panel.detail.action.thorough","panel.detail.action.thorough_note",{path:"path_c",scope:"points_only"},"thorough"):d}
        ${o?R({label:this.i18n.t("panel.detail.action.remove"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("remove")}):d}
      </section>`}_valueRow(e,t){let r=t.origin==="own"?this.i18n.t("panel.detail.source.own"):t.origin==="profile"?this.i18n.t("panel.detail.source.profile",{profile:e.profile??""}):t.origin==="file"?this.i18n.t("panel.detail.source.file"):this.i18n.t("panel.detail.source.default");return ke(this._label(t.key),this._number(t.key,t.value),this._unit(t.key),r,t.own&&t.inherited_value!==null?this.i18n.t("panel.detail.edit.inherits",{value:this._number(t.key,t.inherited_value)}):null)}_calibrateButton(e,t,r,o){let s=this._cover;return R({label:this.i18n.t(e),note:this.i18n.t(t),mark:o,disabled:s===null,onClick:()=>{if(!s)return;let l=s.profile!==null&&!s.profile_missing?s.profile:void 0;this.actions.calibrate({cover:s.unique_id,name:s.name,...r,...r.path&&l?{profile:l}:{}})}})}_edit(e){let t=this.state.detail.form,r=oe.map(s=>e.find(l=>l.key===s)).filter(s=>s!==void 0),o=r.some(s=>x(s.key,t[s.key])!==null);return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.edit.title")}</h2>
      <div class="warn">${this.i18n.t("panel.detail.edit.intro")}</div>
      <div class="fields">
        ${at(r,s=>s.key,De,()=>this._advancedNote(),s=>this._field(s))}
      </div>
      ${A(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||o}
          @click=${this.actions.saveValues}>
          ${this.i18n.t("panel.detail.edit.action.save")}
        </button>`,this.state.applying)}
    </section>`}_advancedNote(){return st(this.i18n.t("panel.common.advanced.title"),this.i18n.t("panel.common.advanced.body"))}_field(e){let t=this.state.detail.form[e.key],r=x(e.key,t),o=e.inherited_value===null?this.i18n.t("panel.detail.edit.empty"):this.i18n.t("panel.detail.edit.inherits",{value:this._number(e.key,e.inherited_value)});return Se({label:this._label(e.key),value:t??"",unit:this._unit(e.key),placeholder:o,error:r?this._problem(e.key,r):null,disabled:this.state.applying,onInput:s=>this.actions.field(e.key,s)})}_travel(e){let t=this.state.detail.form.height,r=x("height",t),o=this.state.detail.preview,s=o&&o.problem===null?oe.filter(l=>o.values[l]!==void 0&&e.values[l]!==void 0):[];return a`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this._label("height")}
      </h2>
      <p class="intro">
        ${this.i18n.t("options.step.calibration_edit.data_description.height")}
      </p>
      ${Se({label:this.i18n.t("panel.review.travel.label"),ariaLabel:this.i18n.t("panel.review.travel.aria"),value:t??"",unit:this.i18n.t("panel.common.unit.centimetres"),placeholder:this.i18n.t("panel.review.travel.placeholder"),error:r?this._problem("height",r):null,disabled:this.state.applying,onInput:l=>this.actions.field("height",l)})}
      ${o&&o.problem!==null?a`<p class="field-error">${this._problem("height",o.problem)}</p>`:d}
      ${s.length>0?a`<table aria-busy=${this.state.detail.previewing?"true":"false"}>
            <thead>
              <tr>
                <th class="what"></th>
                <th>${this.i18n.t("panel.review.before")}</th>
                <th class="after">${this.i18n.t("panel.review.after")}</th>
              </tr>
            </thead>
            <tbody>
              ${s.map(l=>a`<tr>
                  <td class="what">${this._label(l)}</td>
                  <td>${j(this._number(l,e.values[l]),this._unit(l))}</td>
                  <td class="after">
                    ${j(this._number(l,o.values[l]),this._unit(l))}
                  </td>
                </tr>`)}
            </tbody>
          </table>`:d}
      ${A(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||r!==null||C(t)}
          @click=${this.actions.saveTravel}>
          ${this.i18n.t("panel.common.action.save")}
        </button>`,this.state.applying)}
    </section>`}_correct(){return a`<section class="card actions">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.action.correct")}</h2>
      <p class="intro">${this.i18n.t("panel.detail.correct.intro")}</p>
      ${this._calibrateButton("panel.detail.correct.times","panel.detail.correct.times_note",{path:"path_c",scope:"times_only"},"times-only")}
      ${this._calibrateButton("panel.detail.correct.times_rolls","panel.detail.correct.times_rolls_note",{path:"path_c",scope:"times_and_rolls"},"times-and-rolls")}
      ${this._calibrateButton("panel.detail.correct.thorough","panel.detail.correct.thorough_note",{path:"path_c",scope:"points_only"},"points-only")}
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
        ${t?.travel_stays?a`<p class="soft">${this.i18n.t("panel.detail.remove.travel_stays")}</p>`:d}
      </div>
      ${A(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.detail.remove.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-cover-detail")||customElements.define("myhome-cover-detail",lt);var se=["reference_height",...M],Gn=64,ho=new RegExp(`^[A-Za-z0-9_]{1,${Gn}}$`),dt=class extends w{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)&&this.state.dialog===null){if(this.state.profile.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new y,this.state=Y({view:"profile",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[$,k,S,W,ot]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.profile,t=`${e.for??""}|${e.mode}`;if(t===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=t,B(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}get _profile(){let e=this.state.profile.for;return this.state.overview?.profiles.find(t=>t.name===e)??null}get _followers(){let e=this._profile,t=this.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return t.filter(o=>r.has(o.unique_id))}_fullLabel(e){return e==="reference_height"?this.i18n.t("panel.profile.reference_travel"):this.i18n.t(`options.step.profile_edit.data.${e}`)}_label(e){return F(this._fullLabel(e))}_unit(e){let t=ee[e];return t?this.i18n.t(t):""}_number(e,t){return this.i18n.number(t,O[e]??L[e]?.decimals??1)}_problem(e,t){return this.i18n.refusal(t,{key:this._fullLabel(e),min:L[e]?.min??0,max:L[e]?.max??0})}_ownKeys(e){return e.has_own.map(t=>F(this.i18n.t(`options.step.calibration_edit.data.${t}`))).join(", ")}render(){let e=this._profile;if(!this.state.overview)return a`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;if(!e)return a`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.unknown")}</h2>
        ${A(this.i18n.t("panel.common.action.back"),this.actions.back,d)}
      </div>`;let t=this.state.profile.mode;return a`${this._head(e)}
    ${this.state.writeError?a`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:d}
    ${t==="view"?this._view(e):d}
    ${t==="edit"?this._edit():d}
    ${t==="rename"?this._rename(e):d}
    ${t==="delete"?this._delete(e):d}`}_head(e){let r=(this.state.overview?.covers??[]).find(l=>l.unique_id===e.measured_on),o;e.measured_on&&e.measured_on_name&&e.measured_at?(o=this.i18n.t("panel.profile.provenance",{cover:e.measured_on_name,date:this.i18n.date(e.measured_at)}),r&&r.profile!==e.name&&(o+=` · ${r.profile?this.i18n.t("panel.profile.provenance_now_profile",{profile:r.profile}):this.i18n.t("panel.profile.provenance_now_none")}`)):e.measured_on&&e.measured_at?o=this.i18n.t("panel.overview.group.measured_on_gone",{date:this.i18n.date(e.measured_at)}):o=this.i18n.t("panel.profile.provenance_missing");let s=e.editable?this.i18n.t("panel.profile.stored"):this.i18n.t("panel.profile.from_file");return a`<section class="card">
      <p class="sub">${e.missing?o:`${s} · ${o}`}</p>
      ${e.missing?a`<p class="warn" style="margin:12px 0 0">
            ${this.i18n.t("panel.overview.group.values_unknown")}
          </p>`:d}
    </section>`}_view(e){let t=this._followers;return a`${e.missing?d:a`<section class="card">
            <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.values")}</h2>
            <div class="rows">
              ${se.map(r=>r==="reference_height"?e.reference_height===null?d:ke(this._label(r),this._number(r,e.reference_height),this._unit(r),"",null):e.values[r]===void 0?d:ke(this._label(r),this._number(r,e.values[r]),this._unit(r),"",null))}
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
            ${R({label:this.i18n.t("panel.profile.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
            ${R({label:this.i18n.t("panel.profile.action.rename"),disabled:this._locked,onClick:()=>this.actions.mode("rename")})}
            ${R({label:this.i18n.t("panel.profile.action.delete"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("delete")})}
          </section>`:d}`}_follower(e){let r=M.every(o=>e.has_own.includes(o))?this.i18n.t("panel.profile.followers.measured"):e.has_own.length>0?this.i18n.t("panel.profile.followers.adjusted",{keys:this._ownKeys(e)}):this.i18n.t("panel.profile.followers.inherited");return a`<div class="row">
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
      ${e.profile_from_file?a`<span class="from">${this.i18n.t("panel.detail.source.file")}</span>`:d}
    </div>`}_edit(){let e=this._followers,t=this.state.profile.form,r=se.some(s=>x(s,t[s])!==null||C(t[s])),o=e.length===1?this.i18n.t("panel.profile.edit.reach_one"):this.i18n.t("panel.profile.edit.reach_all",{count:e.length});return a`<section class="card">
      <!-- The button that opens this says "Modifica i valori…": the dots are the button's
           promise of a further step, and the heading is that step. -->
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.edit.title")}</h2>
      <div class="warn">
        <strong>${this.i18n.t("panel.profile.edit.reach",{target:o})}</strong>
        ${this.i18n.t("panel.profile.edit.intro")}
      </div>
      <div class="fields">
        ${at(se,s=>s,De,()=>st(this.i18n.t("panel.common.advanced.title"),this.i18n.t("panel.common.advanced.body")),s=>Se({label:this._label(s),value:t[s]??"",unit:this._unit(s),error:C(t[s])?this.i18n.t("panel.common.required"):(()=>{let l=x(s,t[s]);return l?this._problem(s,l):null})(),disabled:this.state.applying,onInput:l=>this.actions.field(s,l)}))}
      </div>
      <h3>${this.i18n.t("panel.profile.impact.title")}</h3>
      <div class="rows" aria-busy=${this.state.profile.impacting?"true":"false"}>
        ${e.map(s=>this._impact(s,r))}
      </div>
      ${A(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||r}
          @click=${this.actions.saveValues}>
          ${e.length===1?this.i18n.t("panel.profile.edit.action.save_one"):this.i18n.t("panel.profile.edit.action.save",{count:e.length})}
        </button>`,this.state.applying)}
    </section>`}_impact(e,t){let r=M.every(l=>e.has_own.includes(l)),o=r?this.i18n.t("panel.profile.impact.state_measured"):e.has_own.length>0?this.i18n.t("panel.profile.impact.state_adjusted"):this.i18n.t("panel.profile.impact.state_inherited"),s;if(r)s=this.i18n.t("panel.profile.impact.no_change");else if(e.height===null)s=this.i18n.t("panel.profile.impact.no_travel");else if(t)s=this.i18n.t("panel.profile.impact.invalid");else{let l=(this.state.profile.impact??[]).find(c=>c.cover_unique_id===e.unique_id);if(!l||l.problem!==null)s=this.i18n.t("panel.common.loading");else if(s=M.filter(p=>!e.has_own.includes(p)&&e.values[p]!==void 0&&l.values[p]!==void 0).map(p=>`${F(this.i18n.t(`options.step.calibration_edit.data.${p}`))} ${this._number(p,e.values[p])} → `+j(this._number(p,l.values[p]),this._unit(p))).join(" · "),e.has_own.length>0){let p=this.i18n.t("panel.profile.impact.kept",{keys:this._ownKeys(e)});s=s?`${s} — ${p}`:p}}return a`<div class="row">
      <span class="what">${e.name}</span>
      <span class="instead">${o}</span>
      <span class="from" style="text-align:left">${s}</span>
    </div>`}_rename(e){let t=this.state.profile.newName,r=t.trim()!==""&&!ho.test(t.trim()),o=r?this.i18n.refusal("invalid_name",{profile:t}):this.state.profile.nameError;return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.rename.title")}</h2>
      <p class="intro">${this.i18n.t("panel.profile.rename.rule")}</p>
      <label class="field-row">
        <span class="what">${this.i18n.t("panel.profile.rename.field")}</span>
        <input
          class="field"
          type="text"
          style="width:220px;text-align:left"
          maxlength=${Gn}
          .value=${t}
          ?disabled=${this.state.applying}
          aria-label=${this.i18n.t("panel.profile.rename.field")}
          aria-invalid=${o?"true":"false"}
          @input=${s=>this.actions.newName(s.target.value)}
        />
      </label>
      ${o?a`<p class="field-error" style="text-align:left">${o}</p>`:d}
      ${A(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
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
      ${A(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.profile.delete.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-profile-card")||customElements.define("myhome-profile-card",dt);var jn="myhome-calibration-cue",Vn=()=>{try{return globalThis.localStorage??null}catch{return null}},Yn=(n=Vn())=>{try{return n?.getItem(jn)!=="off"}catch{return!0}},Xn=(n,i=Vn())=>{try{i?.setItem(jn,n?"on":"off")}catch{}},uo=()=>{let n=globalThis.AudioContext;if(!n)return!1;let i=new n,e=i.createOscillator(),t=i.createGain();return e.type="sine",e.frequency.value=880,t.gain.value=.25,e.connect(t),t.connect(i.destination),e.start(),e.stop(i.currentTime+.08),setTimeout(()=>{try{i.close()}catch{}},200),!0},Zn=n=>{if(!n)return!1;let i=!1;try{let e=globalThis.navigator?.vibrate;typeof e=="function"&&(e.call(globalThis.navigator,80),i=!0)}catch{}try{i=uo()||i}catch{}return i};var Qn=(n,i)=>n.summary?.note?a`<div class="stub">${n.summary.note}</div>`:d;var Jn=(n,i)=>{let e=n.options??[];return e.length===0?d:a`<div class="options" role="group" aria-label=${n.title}>
    ${e.map(t=>a`<button
        class="option"
        type="button"
        aria-pressed=${t.current?"true":"false"}
        @click=${()=>i.fire(t.action)}
      >
        <span class="option-head">
          <strong class="option-title">${t.title}</strong>
          ${t.chip?a`<span class="chip ${t.chipTone??"neutral"}">${t.chip}</span>`:d}
        </span>
        ${t.meta?a`<span class="option-meta">${t.meta}</span>`:d}
      </button>`)}
  </div>`};var er=(n,i)=>{let e=n.progress;if(!e)return d;let t=Math.max(0,Math.min(1,e.fraction))*100;return a`<div class="progress-card">
    ${e.text?a`<p class="instruction">${e.text}</p>`:d}
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
  </div>`};var tr=(n,i)=>{let e=n.press;if(!e)return d;let t=e.state==="moving";return a`
    ${e.instruction?a`<p class="instruction">${e.instruction}</p>`:d}
    <div class="live">
      <div class="live-row">
        <span class="name">${i.i18n.t("panel.screen.motor")}</span>
        <span class="value ${t?"moving":""}">${e.motor??""}</span>
      </div>
      ${e.position?a`<div class="live-row">
            <span class="name">${i.i18n.t("panel.screen.position")}</span>
            <span class="value">${e.position}</span>
          </div>`:d}
    </div>
    ${e.note?a`<div
          class="note ${e.state==="problem"?"error":"success"}"
          role=${e.state==="problem"?"alert":"status"}
        >
          ${e.note}
        </div>`:d}
  `};var mo=n=>{let i=[n.hint?"gap-hint":"",n.error?"gap-error":""].filter(e=>e!=="");return i.length>0?i.join(" "):void 0},ir=(n,i)=>{let e=n.options??[],t=n.field;return e.length===0&&!t?d:a`
    ${e.length>0?a`<div class="options" role="group" aria-label=${n.title}>
          ${e.map(r=>a`<button
              class="option"
              type="button"
              aria-pressed=${r.current?"true":"false"}
              @click=${()=>i.fire(r.action)}
            >
              <strong class="option-title">${r.title}</strong>
              ${r.meta?a`<span class="option-meta">${r.meta}</span>`:d}
            </button>`)}
        </div>`:d}
    ${t?a`<div class="reading" style="margin-top:12px">
          <label for="gap">${t.label}</label>
          <div class="row">
            <input
              id="gap"
              inputmode=${t.inputMode??"decimal"}
              .value=${t.value}
              placeholder=${t.placeholder??""}
              aria-describedby=${mo(t)??d}
              aria-invalid=${t.error?"true":"false"}
              @input=${r=>i.fire("field",r.target.value)}
            />
            ${t.unit?a`<span class="unit">${t.unit}</span>`:d}
          </div>
          ${t.hint?a`<p class="hint" id="gap-hint">${t.hint}</p>`:d}
          ${t.error?a`<p class="error" id="gap-error" role="alert">${t.error}</p>`:d}
        </div>`:d}
  `};var vo=n=>{let i=[n.hint?"reading-hint":"",n.error?"reading-error":""].filter(e=>e!=="");return i.length>0?i.join(" "):void 0},nr=(n,i)=>{let e=n.field;return e?a`<div class="reading ${e.big===!1?"":"big"}">
    <label for="reading">${e.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode=${e.inputMode??"decimal"}
        .value=${e.value}
        placeholder=${e.placeholder??""}
        aria-describedby=${vo(e)??d}
        aria-invalid=${e.error?"true":"false"}
        @input=${t=>i.fire("field",t.target.value)}
      />
      ${e.unit?a`<span class="unit">${e.unit}</span>`:d}
    </div>
    ${e.hint?a`<p class="hint" id="reading-hint">${e.hint}</p>`:d}
    ${e.error?a`<p class="error" id="reading-error" role="alert">${e.error}</p>`:d}
  </div>`:d};var Yt=(n,i)=>a`
  <div class="summary-row">
    <span class="label">${n.label}</span>
    ${n.before?a`<span class="before"
          ><span class="sr-only">${i.i18n.t("panel.review.before")} </span>${n.before}</span
        >`:d}
    <span class="after"
      ><span class="sr-only">${i.i18n.t("panel.review.after")} </span>${n.after}</span
    >
  </div>
`,rr=(n,i)=>a`
  <div class="summary-group">
    <p class="group-title">${n.title}</p>
    <div class="summary">${n.rows.map(e=>Yt(e,i))}</div>
  </div>
`,or=(n,i)=>{let e=n.summary;return e?a`
    <div class="summary">
      ${e.rows.map(t=>Yt(t,i))}
      ${(e.more??[]).map(t=>Yt(t,i))}
      ${(e.lines??[]).map(t=>a`<p class="line">${t}</p>`)}
      ${e.note?a`<p class="note-line">${e.note}</p>`:d}
    </div>
    ${e.sideEffects?rr(e.sideEffects,i):d}
    ${(e.affected??[]).map(t=>rr(t,i))}
    ${e.code?a`${e.codeLabel?a`<p class="code-label">${e.codeLabel}</p>`:d}<pre class="code">${e.code}</pre>`:d}
    ${(e.disclose??[]).length>0?a`<div class="disclose">
          ${(e.disclose??[]).map(t=>a`<button
              class="cta text"
              type="button"
              aria-expanded=${t.open?"true":"false"}
              data-disclose=${t.action}
              @click=${()=>i.fire(t.action)}
            >
              ${t.label}
            </button>`)}
        </div>`:d}
  `:d};var sr=(n,i)=>n.summary?.rows?.length?a`<div class="summary">
    ${n.summary.rows.map(e=>a`<div class="summary-row">
        <span class="label">${e.label}</span>
        <span class="after">${e.after}</span>
      </div>`)}
    ${n.summary.note?a`<p class="note-line">${n.summary.note}</p>`:d}
  </div>`:d;var ar=m`.text-column{min-width:0}.phase{margin:0 0 8px;font-size:12px;color:var(--myhome-text-soft)}.new-text{display:inline-block;margin:0 0 12px;background:var(--myhome-info-pastel);border-radius:10px;padding:3px 10px;font-size:12px;color:var(--myhome-text-soft)}.screen-title{margin:0 0 12px;font-size:20px;font-weight:500;line-height:1.3;display:flex;align-items:center;gap:10px}.outcome-icon{width:32px;height:32px;flex:0 0 32px;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;font-weight:600}.outcome-icon.saved{background:var(--myhome-success-pastel);color:var(--myhome-success-ink)}.outcome-icon.saved:before{content:"✓"}.outcome-icon.cancelled{background:var(--myhome-error-pastel);color:var(--myhome-error-ink)}.outcome-icon.cancelled:before{content:"✕"}.outcome-icon.expired{background:var(--myhome-warning-pastel);color:var(--myhome-warning-ink)}.outcome-icon.expired:before{content:"⧗"}.outcome-icon.problem{background:var(--myhome-error-pastel);color:var(--myhome-error-ink)}.outcome-icon.problem:before{content:"!"}.drawing{height:230px;border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);margin:0 0 16px;background-color:var(--myhome-drawing-paper);background-repeat:no-repeat}.prose p{margin:0 0 12px;font-size:14.5px;line-height:1.6;text-wrap:pretty}.prose ul{margin:0 0 12px;padding-left:20px;font-size:14.5px;line-height:1.6}.prose .md-image{display:block;max-width:100%;border-radius:var(--myhome-radius);margin:0 0 12px}button.big{width:100%;min-height:64px;border:none;border-radius:16px;font:inherit;font-size:16px;font-weight:600;cursor:pointer;background:var(--myhome-primary);color:var(--myhome-text-on-primary);box-shadow:var(--myhome-shadow)}button.big.moving{background:var(--myhome-accent);color:var(--myhome-text-on-accent)}button.big[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default;box-shadow:none}.options{display:flex;flex-direction:column;gap:8px;margin:4px 0 0}.option{text-align:left;border-radius:10px;font:inherit;padding:14px;min-height:56px;cursor:pointer;color:inherit;border:1px solid var(--myhome-field-border);background:var(--myhome-card)}.option[aria-pressed=true]{border-color:var(--myhome-primary-ink);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.option .option-head{display:flex;align-items:center;gap:8px}.option .option-title{font-weight:500;flex:1;font-size:14.5px;line-height:1.4}.option .option-meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:3px}.live{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:14px 16px;display:flex;flex-direction:column;gap:8px;font-size:14px}.live-row{display:flex;justify-content:space-between;gap:12px}.live-row .name{color:var(--myhome-text-soft)}.live-row .value{font-variant-numeric:tabular-nums;font-weight:500}.live-row .value.moving{color:var(--myhome-warning-ink);animation:myhome-pulse 1.2s ease-in-out infinite}@keyframes myhome-pulse{0%,to{opacity:1}50%{opacity:.55}}.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.chip.measured{background:var(--myhome-primary-pastel);color:var(--myhome-text);box-shadow:inset 0 0 0 1px var(--myhome-primary)}.chip.adjusted{background:var(--myhome-accent-pastel);color:var(--myhome-text)}.instruction{margin:0 0 16px;font-size:16.5px;line-height:1.5;font-weight:500}.note{margin:14px 0 0;border-radius:8px;padding:12px 14px;font-size:14px;line-height:1.55}.note.success{background:var(--myhome-success-pastel)}.note.error{background:var(--myhome-error-pastel)}.note.info{background:var(--myhome-info-pastel)}.progress-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px}.progress-track{height:8px;border-radius:4px;background:var(--myhome-background-soft);overflow:hidden}.progress-bar{height:100%;background:var(--myhome-primary);border-radius:4px;transition:width .1s linear}.progress-eta{margin:10px 0 0;font-size:13px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}.reading{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:4px 0 0}.reading label{display:block;font-size:13.5px;margin:0 0 8px}.reading .row{display:flex;align-items:center;gap:10px}.reading input{flex:1;min-width:0;height:56px;border-radius:10px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:inherit;padding:0 14px;font:inherit;font-size:26px;font-variant-numeric:tabular-nums}.reading.big input{height:64px;font-size:32px}.reading .unit{font-size:16px;color:var(--myhome-text-soft)}.reading.big .unit{font-size:18px}.reading .hint{margin:8px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.reading .error{margin:8px 0 0;font-size:12.5px;color:var(--myhome-error-ink);line-height:1.5}.summary{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:8px 16px;margin:4px 0 14px}.summary-row{display:flex;align-items:baseline;gap:8px;padding:9px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.summary-row:last-of-type{border-bottom:none}.summary-row .label{flex:1 1 130px;color:var(--myhome-text-soft)}.summary-row .before{color:var(--myhome-text-soft);font-variant-numeric:tabular-nums;text-decoration:line-through;opacity:.7}.summary-row .after{font-variant-numeric:tabular-nums;font-weight:500}.summary .note-line{margin:10px 0;font-size:12.5px;color:var(--myhome-text-soft)}.code{background:var(--myhome-background-soft);border-radius:8px;padding:12px 14px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-x:auto}.stub{margin:4px 0 0;background:var(--myhome-info-pastel);border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.55}.aside{margin:0 0 12px;font-size:13.5px;line-height:1.55;color:var(--myhome-text-soft)}.read-only{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;margin:12px 16px 0;padding:12px 14px;border-radius:8px;background:var(--myhome-warning-pastel);font-size:13.5px;line-height:1.5}.cue{display:flex;align-items:center;gap:10px;margin:14px 2px 0;min-height:44px;font-size:13.5px;color:var(--myhome-text-soft);cursor:pointer}.cue input{width:20px;height:20px;flex:0 0 20px;accent-color:var(--myhome-primary)}.summary-group{margin:12px 0 0}.summary-group>.group-title{margin:0 0 4px;font-size:13px;font-weight:500}.summary .line{margin:10px 0 0;font-size:12.5px;line-height:1.55;color:var(--myhome-text-soft)}.disclose{display:flex;flex-direction:column;gap:6px;margin:12px 0 0}.code-label{margin:14px 0 6px;font-size:12.5px;color:var(--myhome-text-soft)}@media(min-width:900px){.read-only{margin:0 auto;max-width:1080px;width:calc(100% - 64px)}}`;var Re=class extends w{constructor(){super();this._fire=(e,t)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:e,value:t,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new y}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[$,k,S,W,ne,ar,m`:host{display:block;background:transparent}.screen{width:100%;max-width:480px;margin:0 auto;display:flex;flex-direction:column;position:relative}.pane{flex:1;padding:16px 16px 230px}.right{min-width:0}.footer{position:fixed;bottom:0;left:50%;transform:translate(-50%);width:100%;max-width:480px;padding:36px 16px calc(12px + env(safe-area-inset-bottom,0px));background:linear-gradient(to top,var(--myhome-background) calc(100% - 36px),transparent);z-index:25;display:flex;flex-direction:column;gap:10px}@media(min-width:900px){.screen{max-width:100%}.pane{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:0 44px;align-items:start;width:100%;max-width:1080px;margin:0 auto;padding:24px 32px 48px}.pane.single{display:block;max-width:560px}.right{position:sticky;top:76px}.footer{position:static;transform:none;width:auto;max-width:none;padding:0;background:none;margin-top:20px}}`]}focusEntry(e){let t=this.shadowRoot;if(!t)return!1;let o=(e==="primary"?t.querySelector("button.big:not([disabled])"):null)??t.querySelector("h1.screen-title");return o?(o.focus(),!0):!1}_renderOperative(e,t){switch(e.model){case"scelta":return Jn(e,t);case"pos":return er(e,t);case"click":return tr(e,t);case"controllo":return ir(e,t);case"metro":return nr(e,t);case"riepilogo":return or(e,t);case"esito":return sr(e,t);case"lettura":return Qn(e,t);default:return d}}_renderFooter(e,t){let r=e.secondary??[];return!e.primary&&r.length===0?d:a`<div class="footer">
      ${e.primary?a`<button
            class="big ${e.press?.state==="moving"?"moving":""}"
            type="button"
            data-big
            ?disabled=${e.primary.disabled}
            @click=${()=>this._fire(e.primary.action)}
          >
            ${e.primary.label}
          </button>`:d}
      ${r.map(o=>a`<button
          class="cta ${o.kind==="text"?"text":"secondary"}"
          type="button"
          ?disabled=${o.disabled}
          @click=${()=>t.fire(o.action)}
        >
          ${o.label}
        </button>`)}
    </div>`}render(){let e=this.model;if(!e)return d;let t={i18n:this.i18n,fire:this._fire},r=e.model==="pos",o=e.image?bi(e.image):null,s=(e.image?.alt??"")!=="";return a`<div class="screen">
      ${e.readOnly?a`<div class="read-only" role="status">
            <span>${e.readOnly.text}</span>
            <button
              class="cta secondary"
              type="button"
              data-take-control
              @click=${()=>this._fire(e.readOnly.action)}
            >
              ${e.readOnly.label}
            </button>
          </div>`:d}
      <div class="pane ${r?"single":""}">
        <div class="text-column">
          ${e.phase?a`<p class="phase">
                ${this.i18n.t("panel.screen.phase",{phase:e.phase.label,index:e.phase.index,count:e.phase.count})}
              </p>`:d}
          ${e.newText?a`<p class="new-text">${this.i18n.t("panel.screen.new_text")}</p>`:d}
          <h1 class="screen-title" tabindex="-1">
            ${e.outcome?a`<span class="outcome-icon ${e.outcome}" aria-hidden="true"></span>`:d}
            <span>${e.title}</span>
          </h1>
          ${o?a`<div
                class="drawing"
                role=${s?"img":d}
                aria-label=${s?e.image?.alt??"":d}
                aria-hidden=${s?d:"true"}
                style=${Ye(o)}
              ></div>`:d}
          ${e.body?a`<div class="prose">${J(e.body)}</div>`:d}
          ${(e.lines??[]).map(l=>a`<p class="aside">${l}</p>`)}
          ${e.note?a`<div class="note ${e.note.tone}" role=${e.note.tone==="error"?"alert":"status"}>
                ${e.note.text}
              </div>`:d}
        </div>
        <div class="right">
          ${this._renderOperative(e,t)}
          ${e.toggle?a`<label class="cue">
                <input
                  type="checkbox"
                  .checked=${e.toggle.checked}
                  @change=${l=>this._fire(e.toggle.action,l.target.checked?"on":"off")}
                />
                <span>${e.toggle.label}</span>
              </label>`:d}
          ${this._renderFooter(e,t)}
        </div>
      </div>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",Re);var Xt="cover:",lr=n=>n.startsWith(Xt)?n.slice(Xt.length):null,fo=(n,i)=>i.origin==="inherited"?n.t("panel.overview.cover.origin_inherited"):i.origin==="adjusted"?n.t("panel.overview.cover.origin_adjusted"):n.origin(i.origin,i.profile),go=n=>n.origin==="measured"?"measured":n.origin==="adjusted"?"adjusted":"neutral",dr=(n,i)=>{let e=i.map(t=>({title:t.name,meta:jt(n,t,!1),chip:fo(n,t),chipTone:go(t),action:`${Xt}${t.unique_id}`}));return{id:"wizard.pick",model:"scelta",title:n.t("panel.wizard.pick.title"),body:n.t("panel.wizard.pick.body"),options:e,secondary:[{label:n.t("panel.common.action.back"),action:te,kind:"text"}],announce:n.t("panel.wizard.pick.title")}};var cr=m`.exit-backdrop{position:fixed;inset:0;background:#0006;z-index:60}.exit{position:fixed;left:16px;right:16px;top:50%;transform:translateY(-50%);margin:0 auto;max-width:400px;box-sizing:border-box;background:var(--myhome-card);color:var(--myhome-text);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);z-index:61;padding:20px}.exit h2{margin:0 0 8px;font-size:18px;font-weight:500}.exit p{margin:0 0 16px;font-size:13.5px;line-height:1.55;color:var(--myhome-text-soft)}.exit .foot{display:flex;gap:10px;justify-content:flex-end}.exit .foot button{flex:1 1 0;min-width:0;min-height:44px;padding:0 10px;border:none;border-radius:22px;font:inherit;font-size:13.5px;font-weight:500;cursor:pointer}.exit .foot .stay{background:var(--myhome-primary-faint);color:var(--myhome-primary-ink)}.exit .foot .leave{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}`,pr=n=>{let{i18n:i}=n;return a`
    <div class="exit-backdrop" aria-hidden="true" @click=${n.onStay}></div>
    <div
      class="exit"
      role="dialog"
      aria-modal="true"
      aria-labelledby="exit-title"
      data-exit-dialog
      data-focus-root
    >
      <h2 id="exit-title">${i.t("panel.wizard.exit.title")}</h2>
      <p>${i.t("panel.wizard.exit.body")}</p>
      <div class="foot">
        <button class="stay" type="button" data-exit-stay @click=${n.onStay}>
          ${i.t("panel.wizard.exit.stay")}
        </button>
        <button class="leave" type="button" data-exit-leave @click=${n.onLeave}>
          ${i.t("panel.wizard.exit.leave")}
        </button>
      </div>
    </div>
  `};var _o={refresh:()=>{},act:()=>{},stop:()=>{},save:()=>{},cancel:()=>{},claim:()=>{},claimAndCancel:()=>{},force:()=>{},exit:()=>{},again:()=>{},start:()=>{},endOther:()=>{},ask:()=>{},openFlow:()=>{},openCover:()=>{},back:()=>{}},wo=100,ct=class extends w{constructor(){super();this._broken=null;this._reported=!1;this._typed=null;this._typedFor="";this._showAll=!1;this._showAffected=!1;this._cue=Yn();this._skewMs=0;this._skewFor="";this._clock=null;this._painted=0;this._focusedFor="";this._signalledFor="";this._trap=new q;this._return=new Ke;this._trapped=!1;this._onKey=e=>{e.key==="Escape"&&this.state.session&&(e.stopPropagation(),this.actions.exit(!this.state.wizardExit))};this._onScreenAction=e=>{let t=e.detail,r=t?.action??"",o=t?.value;if(r==="field"){this._typed=o??"";return}if(r===Ht){this.actions.act("submit",this._typed??"");return}if(r.startsWith(be)){this.actions.act("submit",r.slice(be.length));return}let s=lr(r);if(s!==null){let l=(this.state.overview?.covers??[]).find(c=>c.unique_id===s);this.actions.start({cover:s,name:l?.name});return}if(r.startsWith(D)){this.actions.act(r.slice(D.length));return}if(r.startsWith(ye)){this.actions.save(r.slice(ye.length));return}if(r===Ft){this.actions.stop();return}if(r===Nt){this.actions.claim();return}if(r===Wt){this._cue=o!=="off",Xn(this._cue),this.requestUpdate();return}if(r===qt){this._showAll=!this._showAll,this.requestUpdate();return}if(r===Bt){this._showAffected=!this._showAffected,this.requestUpdate();return}if(r===qe){this.actions.again();return}if(r===Ut){let l=this.state.session?.cover?.unique_id;l&&this.actions.openCover(l);return}r===te&&this.actions.back()};this.i18n=new y,this.state={},this.actions=_o,this.hass=null}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1},hass:{attribute:!1}}}static{this.styles=[$,k,S,ne,cr,m`:host{display:block}.card{padding:16px}.card+.card{margin-top:16px}.card.problem{background:var(--myhome-error-pastel)}h2{margin:0 0 8px;font-size:18px}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.soft{color:var(--myhome-text-soft);font-size:13px;margin-top:8px}`]}connectedCallback(){super.connectedCallback(),this.addEventListener("keydown",this._onKey)}disconnectedCallback(){this.removeEventListener("keydown",this._onKey),this._stopClock(),this._trap.release(),this._trapped=!1,super.disconnectedCallback()}render(){if(this._broken)return this._renderBroken();try{return a`${this._renderSession()}${this._renderTrouble()}${this._renderExit()}`}catch(e){return this._fail(e),this._renderBroken()}}updated(){let e=this.state.session??null;if(this._followClock(e),this._followExit(),!e||this._broken)return;let t=`${e.session_id}:${e.state}:${e.step??""}`;if(t!==this._focusedFor){this._focusedFor=t;let o=this.shadowRoot?.querySelector("myhome-screen"),s=e.substate==="awaiting_endpoint"?"primary":"title";o?.updateComplete.then(()=>o.focusEntry(s))}let r=`${e.session_id}:${e.substate==="awaiting_endpoint"?e.step:""}`;e.substate==="awaiting_endpoint"&&r!==this._signalledFor&&(this._signalledFor=r,Zn(this._cue))}_renderSession(){let e=this.state.session??null;if(!e)return this._renderPick();this._rememberField(e);let t=fn(e,{i18n:this.i18n,now:Date.now(),skewMs:this._skew(e),typed:this._typed,position:this._position(e),readOnly:this._readOnly(e),showAll:this._showAll,showAffected:this._showAffected,cue:this._cue,profiles:this.state.overview?.profiles??[]});return a`<div data-wizard>
      ${Ge(t.announce??"")}${yn(t.alert??"")}
      <myhome-screen
        .model=${t}
        .i18n=${this.i18n}
        @myhome-screen-action=${this._onScreenAction}
      ></myhome-screen>
    </div>`}_renderPick(){let e=this.state.overview?.covers??[];return e.length===0?a`<div class="card" data-wizard-empty>
        <h2>${this.i18n.t("panel.overview.no_basic_covers_title")}</h2>
        <p>${this.i18n.t("panel.overview.no_basic_covers")}</p>
        <div class="actions">
          <button class="cta text" type="button" @click=${()=>this.actions.back()}>
            ${this.i18n.t("panel.common.action.back")}
          </button>
        </div>
      </div>`:a`<div data-wizard-pick>
      <myhome-screen
        .model=${dr(this.i18n,e)}
        .i18n=${this.i18n}
        @myhome-screen-action=${this._onScreenAction}
      ></myhome-screen>
    </div>`}_readOnly(e){let t=e.owner?.client_id;return t!==void 0&&t!==this.state.clientId}_position(e){let t=e.cover?.entity_id,r=t?this.hass?.states?.[t]?.attributes?.current_position:void 0;return typeof r=="number"&&Number.isFinite(r)?r:null}_skew(e){let t=`${e.session_id}:${e.revision}`;if(t!==this._skewFor){this._skewFor=t;let r=Date.parse(e.server_time);this._skewMs=Number.isNaN(r)?0:Date.now()-r}return this._skewMs}_rememberField(e){let t=e.form,r=`${e.session_id}:${e.step??""}:${t?.field??""}`;if(r===this._typedFor)return;this._typedFor=r,this._showAll=!1,this._showAffected=!1;let o=t&&t.kind!=="choice"?t.suggested:null;this._typed=o==null?"":typeof o=="number"?this.i18n.number(o,1):o}_followExit(){let e=!!this.state.wizardExit;if(e===this._trapped)return;if(this._trapped=e,!e){this._trap.release(),this._return.restore();return}this._return.remember(this.getRootNode()?.activeElement??null);let t=this.shadowRoot?.querySelector("[data-exit-dialog]");t&&this._trap.hold(t)}_followClock(e){e?.movement?.started_at!=null&&!this._broken?this._startClock():this._stopClock()}_startClock(){if(this._clock!==null)return;let e=globalThis.requestAnimationFrame;if(typeof e!="function")return;let t=()=>{this._clock=e(t);let r=Date.now();r-this._painted<wo||(this._painted=r,this.requestUpdate())};this._clock=e(t)}_stopClock(){if(this._clock===null)return;let e=globalThis.cancelAnimationFrame;typeof e=="function"&&e(this._clock),this._clock=null}_renderExit(){return this.state.wizardExit?pr({i18n:this.i18n,onStay:()=>this.actions.exit(!1),onLeave:()=>{this.actions.exit(!1),this.actions.cancel()}}):d}_renderTrouble(){let e=this.state.sessionError??null;if(!e)return d;if(e.error.translation_key==="already_calibrating")return this._renderBusy(e);let t=e.freedAt?this.i18n.time(e.freedAt):"";return a`<div class="card problem" role="alert" data-session-trouble>
      <h2>${this.i18n.t("panel.wizard.trouble.title")}</h2>
      <p>
        ${this.i18n.refusal(e.error.translation_key,e.error.translation_placeholders??{})}
      </p>
      ${e.recovery.includes("wait")?a`<p class="soft">
            ${t?this.i18n.t("panel.wizard.trouble.freed",{time:t}):this.i18n.t("panel.wizard.trouble.freed_later")}
          </p>`:d}
      <div class="actions">
        ${e.recovery.map(r=>this._recoveryButton(r))}
      </div>
    </div>`}_renderBusy(e){let t=e.error.translation_placeholders??{},r=t.cover??this.state.wizardIntent?.name??"",o=this.state.busy.service?"reserved":t.by??"other",s=o==="panel"?this.i18n.t("panel.wizard.busy.panel",{cover:r}):o==="other"?this.i18n.t("panel.wizard.busy.other",{cover:r}):this.i18n.t("panel.wizard.busy.service");return this.state.busy.ask==="end_other"?a`<div class="card problem" role="alert" data-session-busy>
        <h2>${this.i18n.t("panel.wizard.busy.title")}</h2>
        <p data-busy-question>${this.i18n.t("panel.wizard.busy.end_other_confirm")}</p>
        <div class="actions">
          <button
            class="cta text"
            type="button"
            data-busy="confirm"
            @click=${()=>this.actions.endOther()}
          >
            ${this.i18n.t("panel.wizard.busy.end_other")}
          </button>
          <button
            class="cta text"
            type="button"
            data-busy="keep"
            @click=${()=>this.actions.ask(null)}
          >
            ${this.i18n.t("panel.common.action.cancel")}
          </button>
        </div>
      </div>`:a`<div class="card problem" role="alert" data-session-busy>
      <h2>${this.i18n.t("panel.wizard.busy.title")}</h2>
      <p>${s}</p>
      <div class="actions">
        ${o==="panel"?a`<button
              class="cta text"
              type="button"
              data-busy="resume"
              @click=${()=>this.actions.refresh()}
            >
              ${this.i18n.t("panel.banner.measuring.action.resume")}
            </button>`:d}
        ${o==="other"?a`<button
                class="cta text"
                type="button"
                data-busy="end-other"
                @click=${()=>this.actions.ask("end_other")}
              >
                ${this.i18n.t("panel.wizard.busy.end_other")}
              </button>
              <button
                class="cta text"
                type="button"
                data-busy="configure"
                @click=${l=>this.actions.openFlow(l.currentTarget)}
              >
                ${this.i18n.t("panel.common.action.configure")}
              </button>`:d}
        <button class="cta text" type="button" data-busy="back" @click=${()=>this.actions.back()}>
          ${this.i18n.t("panel.common.action.back")}
        </button>
      </div>
    </div>`}_recoveryButton(e){if(e==="wait")return d;let t=e==="claim"?this.i18n.t("panel.wizard.action.claim"):e==="claim_cancel"?this.i18n.t("panel.wizard.action.claim_cancel"):e==="force"?this.i18n.t("panel.wizard.action.force"):this.i18n.t("panel.common.action.retry");return a`<button class="cta text" type="button" data-recovery=${e} @click=${e==="claim"?()=>this.actions.claim():e==="claim_cancel"?()=>this.actions.claimAndCancel():e==="force"?()=>this.actions.force():()=>this.actions.refresh()}>
      ${t}
    </button>`}_renderBroken(){return a`<div class="card problem" role="alert" data-render-error>
      <h2>${this.i18n.t("panel.wizard.render_error.title")}</h2>
      <p>${this.i18n.t("panel.wizard.render_error.body")}</p>
      <div class="actions">
        <button
          class="cta text"
          type="button"
          @click=${()=>{this._broken=null,this.requestUpdate()}}
        >
          ${this.i18n.t("panel.common.action.retry")}
        </button>
        <button class="cta text" type="button" @click=${()=>this.actions.cancel()}>
          ${this.i18n.t("panel.wizard.action.end")}
        </button>
      </div>
    </div>`}_fail(e){this._broken=e,this._stopClock(),this._trap.release(),this._trapped=!1,this._reported||(this._reported=!0,console.error("MyHOME panel: the guided calibration could not be drawn",e))}};customElements.get("myhome-wizard")||customElements.define("myhome-wizard",ct);var yo=3e4,bo=7e3,Zt=400,xo=2e3,Qt=class extends w{constructor(){super();this._i18n=new y;this._router=new He;this._store=new Be(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._snackTimer=null;this._previewTimer=null;this._travelTimer=null;this._impactTimer=null;this._followTimer=null;this._followedAt=0;this._sessionClient=null;this._openingSession=!1;this._coverState="";this._drawerBack=null;this._trap=new q;this._returnTo=null;this._listening=Promise.resolve();this._subscribing=0;this._previewSeq=0;this._drawerWasOpen=!1;this._dialogWasOpen=!1;this._onSocketDown=()=>{this._store.state.connection!=="offline"&&(this._store.set({connection:"offline"}),this._store.announce(this._i18n.t("panel.error.no_connection")))};this._onSocketReady=()=>{this._afterReconnect()};this._onReturn=()=>{!this._started||document.hidden||(this._refresh(),this._store.state.route.view==="calibrate"&&this._sessionClient?.resume())};this._closeDrawer=()=>{this._store.state.applying||this._navigate(on(this._drawerBack))};this._assignActions={search:e=>this._store.set({search:e}),room:e=>this._store.set({room:e}),clearFilters:()=>this._store.set({search:"",room:""}),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:(e,t)=>{if(this._locked)return;let{pending:r,withdrawn:o}=Zi(this._store.state.pending,e,t);this._store.set({pending:r,dialog:null,armed:null,writeError:null}),V(this._store.state.route)&&(this._drawerBack=null,this._navigate("/")),this._store.announce(o?this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name}):this._i18n.t("panel.assign.announce.pending",{cover:e.name,target:t===null?this._i18n.t("panel.assign.target_none"):this._i18n.t("panel.assign.target_profile",{profile:t})})),this._schedulePreview()},withdraw:e=>{this._store.set({pending:this._store.state.pending.filter(t=>t.cover!==e.unique_id)}),this._store.announce(this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name})),this._schedulePreview()},discardAll:()=>{this._store.set({...Ue}),this._store.announce(this._i18n.t("panel.assign.announce.discarded"))},reorder:e=>{this._locked||!this._store.state.entryId||(this._store.set({order:e}),this._write(()=>Ti(this.hass.connection,this._store.state.entryId,e),t=>{this._store.set({order:null}),this._store.setOverview(t.overview),this._snack(this._i18n.t("panel.toast.order_saved"),t.undo_token),this._store.announce(this._i18n.t("panel.assign.announce.reordered"))},t=>{this._store.set({order:null,writeError:null}),this._snack(t,null,!1)}))},setOrder:e=>this._store.set({order:e}),drag:e=>this._store.set({drag:e?{cover:e.unique_id,name:e.name,over:null,insert:null}:null}),over:e=>{let t=this._store.state.drag;t&&this._store.set({drag:{...t,over:e?.group??null,insert:e?{...e}:null}})},arm:e=>{this._store.set({armed:e?e.unique_id:null}),e&&this._store.announce(this._i18n.t("panel.assign.announce.armed"))},dialog:e=>this._store.set({dialog:e?e.unique_id:null}),review:e=>{this._store.set({review:e,writeError:null,heightsForced:!1}),e&&this._refreshPreview()},height:(e,t)=>{this._store.set({heights:{...this._store.state.heights,[e]:t}}),this._schedulePreview()},toggleShowAll:()=>this._store.set({showAll:!this._store.state.showAll}),confirm:()=>{this._confirm()},undo:()=>{this._undo()},announce:e=>this._store.announce(e),calibrate:e=>{this._calibrate(e)}};this._detailActions={back:this._closeDrawer,retry:()=>{this._store.set({detail:{...this._store.state.detail,loading:!0,error:null}}),this._loadDetail()},openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:()=>{this._store.set({dialog:this._store.state.detail.for})},mode:e=>{let t=this._store.state.detail,r=this._detailCover,o=e==="edit"?this._detailForm():e==="travel"?{height:r?.height!=null?this._i18n.number(r.height,0):""}:{};this._store.set({detail:{...t,mode:e,form:o,errors:{},preview:null,previewing:!1},writeError:null}),e==="travel"&&this._refreshTravelPreview()},field:(e,t)=>{let r=this._store.state.detail,o=e==="height"&&x("height",t)!==null;o&&(this._previewSeq+=1),this._store.set({detail:{...r,form:{...r.form,[e]:t},...o?{preview:null}:{}}}),e==="height"&&this._scheduleTravelPreview()},saveValues:()=>{this._saveValues()},saveTravel:()=>{this._saveTravel()},remove:()=>{this._removeMeasure()},calibrate:e=>{this._calibrate(e)}};this._profileActions={back:this._closeDrawer,openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),mode:e=>{let t=this._store.state.profile;this._store.set({profile:{...t,mode:e,form:e==="edit"?this._profileForm(this._profileRow):{},errors:{},newName:e==="rename"?t.for??"":"",nameError:"",impact:null,impacting:!1},writeError:null}),e==="edit"&&this._refreshImpact()},field:(e,t)=>{let r=this._store.state.profile;this._store.set({profile:{...r,form:{...r.form,[e]:t}}}),this._scheduleImpact()},newName:e=>this._store.set({profile:{...this._store.state.profile,newName:e,nameError:""}}),saveValues:()=>{this._saveProfile()},rename:()=>{this._renameProfile()},remove:()=>{this._deleteProfile()}};this._bannerActions={resume:()=>this._navigate("/calibrate"),ask:e=>this._store.set({busy:{...this._store.state.busy,ask:e}}),endPanel:()=>{this._store.set({busy:{...this._store.state.busy,ask:null}}),this._cancelSession("force")},endOther:()=>{this._endOther()},openFlow:e=>this._openFlow(e)};this._wizardActions={refresh:()=>{this._readSession()},start:e=>{this._calibrate(e)},endOther:()=>{this._endOther()},ask:e=>this._store.set({busy:{...this._store.state.busy,ask:e}}),openFlow:e=>this._openFlow(e),act:(e,t)=>{this._actSession(e,t)},stop:()=>{this._stopSession()},save:e=>{this._saveSession(e)},cancel:()=>{this._cancelSession("plain")},claim:()=>{this._takeControl()},claimAndCancel:()=>{this._cancelSession("claim")},force:()=>{this._cancelSession("force")},exit:e=>this._store.set({wizardExit:e}),again:()=>{this._store.set({session:null,sessionError:null,wizardIntent:null}),this._navigate("/calibrate")},openCover:e=>this._navigate(an("cover",e)),back:()=>this._navigate("/")};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[$,k,S,ne,kn,Xe,Qe,bn,m`.toolbar{display:flex;align-items:center;gap:8px;padding:0 8px;background:var(--myhome-header);color:var(--myhome-header-text);font-size:20px;font-weight:400;padding-top:env(safe-area-inset-top,0px);height:calc(56px + env(safe-area-inset-top,0px))}.toolbar .title{flex:1;min-width:0;margin:0;font-size:inherit;font-weight:inherit;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar .titles{flex:1;min-width:0}.toolbar .titles .title{font-size:15px;font-weight:500}.toolbar .phase{margin:0;font-size:12px;opacity:.85;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar select.gateway{font:inherit;font-size:13px;max-width:40%;min-height:44px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;padding:0 6px}.toolbar select.gateway option{color:var(--myhome-text);background:var(--myhome-card)}.toolbar button{width:48px;height:48px;flex:0 0 48px;border:0;border-radius:24px;background:transparent;color:inherit;font-size:20px;line-height:1;cursor:pointer}.content{padding:16px;max-width:1200px;margin:0 auto;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}.card.problem{background:var(--myhome-error-pastel);color:var(--myhome-text);padding:16px}.card.waiting{color:var(--myhome-text-soft);padding:16px}.soft{color:var(--myhome-text-soft);font-size:13px;margin-top:8px}.connection{margin:24px 0 0;font-size:12.5px;color:var(--myhome-text-soft)}.offline{display:block;padding:12px 16px;background:var(--myhome-warning-pastel);color:var(--myhome-text);font-size:14px}a{color:var(--myhome-primary-ink)}`]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(e=>this._onRoute(e)),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),this._trap.release(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._unwatchSocket(),this._stopPolling(),this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._previewTimer&&(clearTimeout(this._previewTimer),this._previewTimer=null),this._travelTimer&&(clearTimeout(this._travelTimer),this._travelTimer=null),this._impactTimer&&(clearTimeout(this._impactTimer),this._impactTimer=null),this._followTimer&&(clearTimeout(this._followTimer),this._followTimer=null);let e=this._unsubscribeWs;this._unsubscribeWs=null,e?.().catch(()=>{});let t=this._sessionClient;this._sessionClient=null,this._release(t)}_release(e){e&&e.leave().finally(()=>e.dispose())}shouldUpdate(e){if(e.size>1||!e.has("hass")||this._languageOf(this.hass)!==this._language)return!0;let t=this._coverStateNow();return t!==this._coverState?(this._coverState=t,!0):!1}_coverStateNow(){let e=this._store.state.session?.cover?.entity_id;if(!e)return"";let t=this.hass?.states?.[e];return t?`${t.state}|${String(t.attributes?.current_position??"")}`:""}firstUpdated(){this._bootstrap()}updated(e){if(this._manageDrawerFocus(),e.has("route")&&(this._router.setHostPath(this.route?.path),this._onRoute(this._router.current)),!(!e.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_manageDrawerFocus(){let e=this._store.state,t=V(e.route)&&e.status!=="error",r=e.dialog!==null,o=()=>this.renderRoot.querySelector("[data-drawer]");if(t&&!this._drawerWasOpen)this._returnTo=Kt(this.renderRoot),requestAnimationFrame(()=>{let s=o();s&&this._trap.hold(s,!1)});else if(!t&&this._drawerWasOpen){this._trap.release();let s=this._returnTo;this._returnTo=null,B(()=>s?.isConnected?s:null)}else t&&this._dialogWasOpen&&!r&&requestAnimationFrame(()=>{let s=o();s&&this._trap.hold(s)});this._drawerWasOpen=t,this._dialogWasOpen=r}_languageOf(e){return e?.locale?.language||e?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,this._watchSocket(),await this._loadTexts(),await this._refresh(),await this._loadDetail(),await this._listen(),this._ensureSession(),this._store.state.route.view==="calibrate"&&await this._readSession())}_watchSocket(){let e=this.hass?.connection;e?.addEventListener?.("disconnected",this._onSocketDown),e?.addEventListener?.("ready",this._onSocketReady)}_unwatchSocket(){let e=this.hass?.connection;e?.removeEventListener?.("disconnected",this._onSocketDown),e?.removeEventListener?.("ready",this._onSocketReady)}async _afterReconnect(){this._started&&(this._store.set({connection:this._unsubscribeWs?"live":"polling"}),await this._refresh(),!this._unsubscribeWs&&!this._subscribing&&await this._listen(),this._store.announce(this._i18n.t("panel.common.reconnected")))}async _loadTexts(){let e=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,e)}catch{}this._language=e,this.requestUpdate()}async _refresh(){try{let e=await $i(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(e)}catch(e){this._store.setError(b(e))}}_listen(){this._subscribing+=1;let e=this._listening.then(()=>this._subscribeOnce()).finally(()=>{this._subscribing-=1});return this._listening=e.catch(()=>{}),e}async _subscribeOnce(){let e=this._unsubscribeWs;this._unsubscribeWs=null,await e?.().catch(()=>{});try{let t=await Ri(this.hass.connection,this._store.state.entryId,r=>this._onEvent(r));if(!this.isConnected){t().catch(()=>{});return}this._unsubscribeWs=t,this._store.set({connection:"live"}),this._stopPolling()}catch(t){me(t)||console.warn("MyHOME panel: live updates are not available",b(t)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(e){if(e.type==="overview"){this._store.setOverview(e.overview),this._followPush();return}if(e.type==="session"){let t=this._ensureSession();t?t.apply(e.session):this._store.set({session:e.session});return}if(e.type==="measuring"){let t=this._store.state.overview;if(!t)return;this._store.set({overview:{...t,measuring:e.cover_unique_id?{cover_unique_id:e.cover_unique_id,name:e.name??""}:null}}),e.cover_unique_id&&(this._store.set({armed:null,drag:null}),this._store.announce(this._i18n.t("panel.banner.measuring.body",{cover:e.name??""})))}}_followPush(){if(this._followTimer)return;let e=Math.max(0,xo-(Date.now()-this._followedAt));this._followTimer=setTimeout(()=>{this._followTimer=null,this._followedAt=Date.now(),this._store.state.review&&this._schedulePreview(),this._store.state.detail.for&&this._loadDetail()},e)}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},yo))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}_onRoute(e){let t=this._store.state.route;if(this._drawerBack=rn(this._drawerBack,this._store.state.route,e),this._store.set({route:e}),e.view==="cover"){let r=e.params.id;this._store.state.detail.for!==r&&(this._store.set({detail:{...xe,for:r,loading:!0}}),this._loadDetail())}else this._store.state.detail.for!==null&&this._store.set({detail:xe});if(e.view==="profile"){let r=e.params.name;this._store.state.profile.for!==r&&this._store.set({profile:{...$e,for:r}})}else this._store.state.profile.for!==null&&this._store.set({profile:$e});e.view==="calibrate"?this._openingSession?this._openingSession=!1:(this._store.set({sessionError:null}),this._started&&this._readSession()):t.view==="calibrate"&&(this._openingSession=!1,this._store.set({wizardExit:!1}),this._leaveSession()),this._started&&this._store.set({writeError:null})}get _version(){return this.panel?.config?.version??""}_navigate(e){this._router.navigate(e)}_renderMenuButton(){return this.narrow?ji("ha-menu-button")?a`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:a`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>Vi(this)}
    >
      ☰
    </button>`:d}_renderPlaceholder(e,t){let r={id:"panel.common.not_yet",model:"lettura",title:e,body:t,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return a`<myhome-screen
      .model=${r}
      .i18n=${this._i18n}
      @myhome-screen-action=${o=>{o.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}get _locked(){let e=this._store.state;return e.overview?.measuring!=null||e.applying}async _confirm(){let e=this._store.state,t=e.entryId;if(this._locked||!t||e.pending.length===0)return;if(e.pending.filter(l=>{let c=e.overview?.covers.find(p=>p.unique_id===l.cover);return c!==void 0&&en(c,l)&&ve(e.heights[l.cover])!==null}).length>0){this._store.set({heightsForced:!0}),this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));return}let o=Et(e.pending,e.heights,e.overview?.covers??[]),s=e.order??void 0;this._store.announce(this._i18n.t("panel.assign.announce.applying")),await this._write(()=>Ei(this.hass.connection,t,o,s),l=>{this._store.set({...Ue}),this._store.setOverview(l.overview),this._snack(l.applied===1?this._i18n.t("panel.toast.assigned_one"):this._i18n.t("panel.toast.assigned",{count:l.applied}),l.undo_token)})}async _undo(){let e=this._store.state,t=e.snack?.undoToken;if(!t||!e.entryId)return;let r=e.entryId;this._clearSnack(),await this._write(()=>Oi(this.hass.connection,r,t),o=>{this._store.setOverview(o.overview),this._snack(this._i18n.t("panel.toast.undone"),null)})}async _write(e,t,r){this._store.set({applying:!0,writeError:null});try{let o=await e();this._store.set({applying:!1}),t(o)}catch(o){let s=b(o);this._store.set({applying:!1,writeError:s});let l=this._i18n.refusal(s.translation_key,s.translation_placeholders??{});this._store.announce(l),r?.(l)}}_snack(e,t,r=!0){this._clearSnack(),this._store.set({snack:{message:e,undoToken:t}}),r&&this._store.announce(e),this._snackTimer=setTimeout(()=>{this._snackTimer=null,this._store.set({snack:null})},bo)}_clearSnack(){this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._store.set({snack:null})}_schedulePreview(){this._store.state.review&&(this._previewTimer&&clearTimeout(this._previewTimer),this._previewTimer=setTimeout(()=>{this._previewTimer=null,this._refreshPreview()},Zt))}async _refreshPreview(){let e=this._store.state;if(!e.entryId||e.pending.length===0){this._store.set({preview:null});return}let t=++this._previewSeq;this._store.set({previewing:!0});try{let r=await Ie(this.hass.connection,e.entryId,Et(e.pending,e.heights,e.overview?.covers??[]));t===this._previewSeq&&this._store.set({preview:r.items,previewing:!1})}catch(r){t===this._previewSeq&&this._store.set({previewing:!1}),me(r)||console.warn("MyHOME panel: the preview could not be read",b(r))}}get _detailCover(){let e=this._store.state,t=e.detail.for;return e.overview?.covers.find(r=>r.unique_id===t)??null}async _loadDetail(){let e=this._store.state,t=e.detail.for;if(!(!this._started||!this.hass||!t||!e.entryId))try{let r=await Si(this.hass.connection,e.entryId,t);if(this._store.state.detail.for!==t)return;this._store.set({detail:{...this._store.state.detail,answer:r,loading:!1,error:null}})}catch(r){if(this._store.state.detail.for!==t)return;this._store.set({detail:{...this._store.state.detail,answer:null,loading:!1,error:b(r)}})}}_detailForm(){let e=this._store.state.detail.answer,t={};for(let r of oe){let o=e?.keys.find(s=>s.key===r);t[r]=o&&o.own?this._i18n.number(o.value,O[r]??1):""}return t}async _saveValues(){let e=this._store.state,t=e.detail.for;if(this._locked||!t||!e.entryId)return;let r={};for(let c of oe){let p=e.detail.form[c];if(x(c,p)!==null)return;r[c]=C(p)?null:I(p??"")}let o=Object.values(r).every(c=>c===null),s=this._detailCover?.name??"",l=e.entryId;await this._write(()=>Ai(this.hass.connection,l,t,r),c=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{}}}),this._store.setOverview(c.overview),this._loadDetail(),this._snack(o?this._i18n.t("panel.toast.measure_removed",{cover:s,destination:this._destinationOf(c.overview,t)}):this._i18n.t("panel.toast.values_saved",{cover:s}),c.undo_token)})}async _saveTravel(){let e=this._store.state,t=e.detail.for,r=e.detail.form.height;if(this._locked||!t||!e.entryId||C(r)||x("height",r))return;let o=I(r??""),s=this._detailCover?.name??"",l=e.entryId;await this._write(()=>Ci(this.hass.connection,l,t,o),c=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{},preview:null}}),this._store.setOverview(c.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.travel_saved",{cover:s}),c.undo_token)})}async _removeMeasure(){let e=this._store.state,t=e.detail.for;if(this._locked||!t||!e.entryId)return;let r=this._detailCover?.name??"",o=e.entryId;await this._write(()=>Pi(this.hass.connection,o,t),s=>{this._store.set({detail:{...this._store.state.detail,mode:"view"}}),this._store.setOverview(s.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.measure_removed",{cover:r,destination:s.falls_back_to==="profile"?this._i18n.t("panel.detail.destination.profile",{profile:s.profile??""}):s.falls_back_to==="file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}),s.undo_token)})}_destinationOf(e,t){let r=e.covers.find(o=>o.unique_id===t);return r?.origin==="inherited"||r?.origin==="adjusted"?this._i18n.t("panel.detail.destination.profile",{profile:r.profile??""}):r?.origin==="from_the_file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}_scheduleTravelPreview(){this._travelTimer&&clearTimeout(this._travelTimer),this._travelTimer=setTimeout(()=>{this._travelTimer=null,this._refreshTravelPreview()},Zt)}async _refreshTravelPreview(){let e=this._store.state,t=this._detailCover,r=e.detail.form.height;if(!e.entryId||!t||C(r)||x("height",r)!==null){this._store.set({detail:{...this._store.state.detail,preview:null}});return}let o=++this._previewSeq;this._store.set({detail:{...this._store.state.detail,previewing:!0}});try{let s=await Ie(this.hass.connection,e.entryId,[{...Tt(t),height:I(r??"")}]);if(o!==this._previewSeq)return;this._store.set({detail:{...this._store.state.detail,preview:s.items[0]??null,previewing:!1}})}catch(s){o===this._previewSeq&&this._store.set({detail:{...this._store.state.detail,previewing:!1}}),me(s)||console.warn("MyHOME panel: the preview could not be read",b(s))}}_openFlow(e){nn({source:e,entryId:this._store.state.entryId,onLeaving:()=>this._store.announce(this._i18n.t("panel.common.opens_configure"))})}_drawerTitle(){let e=this._store.state,t=e.route;if(t.view==="cover"){let r=this._detailCover;return r?r.name:this._i18n.t("panel.detail.title")}return t.view==="profile"?e.overview?.profiles.some(o=>o.name===t.params.name)?this._i18n.t("panel.profile.name",{profile:t.params.name}):this._i18n.t("panel.profile.title"):this._i18n.t("panel.overview.title")}_title(){let e=this._store.state;return e.route.view==="calibrate"?e.session?.cover?.name??e.wizardIntent?.name??this._i18n.t("panel.wizard.title"):this._i18n.t("panel.overview.title")}get _profileRow(){let e=this._store.state;return e.overview?.profiles.find(t=>t.name===e.profile.for)??null}_followersOf(e){let t=this._store.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return t.filter(o=>r.has(o.unique_id))}_profileForm(e){let t={};for(let r of se){let o=r==="reference_height"?e?.reference_height:e?.values[r];t[r]=o==null?"":this._i18n.number(o,O[r]??0)}return t}_typedProfile(){let e=this._store.state.profile.form,t={};for(let r of se){if(C(e[r])||x(r,e[r])!==null)return null;t[r]=I(e[r]??"")}return t}async _saveProfile(){let e=this._store.state,t=e.profile.for,r=this._typedProfile();if(this._locked||!t||!e.entryId||!r)return;let{reference_height:o,...s}=r,l=e.entryId;await this._write(()=>zi(this.hass.connection,l,t,s,o),c=>{this._store.set({profile:{...this._store.state.profile,mode:"view",impact:null}}),this._store.setOverview(c.overview),this._snack(c.affected.length===1?this._i18n.t("panel.toast.profile_saved_one",{profile:t}):this._i18n.t("panel.toast.profile_saved",{profile:t,count:c.affected.length}),c.undo_token)})}async _renameProfile(){let e=this._store.state,t=e.profile.for,r=e.profile.newName.trim();if(this._locked||!t||!e.entryId||!r||r===t)return;let o=e.entryId;await this._write(()=>Ii(this.hass.connection,o,t,r),s=>{this._store.setOverview(s.overview),this._navigate(`/profile/${encodeURIComponent(r)}`),this._snack(this._i18n.t("panel.toast.profile_renamed",{profile:r}),s.undo_token)},s=>this._store.set({profile:{...this._store.state.profile,nameError:s},writeError:null}))}async _deleteProfile(){let e=this._store.state,t=e.profile.for;if(this._locked||!t||!e.entryId)return;let r=e.entryId;await this._write(()=>Mi(this.hass.connection,r,t),o=>{this._store.setOverview(o.overview),this._navigate("/"),this._snack(this._i18n.t("panel.toast.profile_deleted",{profile:t}),o.undo_token)})}_scheduleImpact(){this._impactTimer&&clearTimeout(this._impactTimer),this._impactTimer=setTimeout(()=>{this._impactTimer=null,this._refreshImpact()},Zt)}async _refreshImpact(){let e=this._store.state,t=this._typedProfile(),r=e.profile.for,o=this._followersOf(this._profileRow);if(!e.entryId||!r||!t||o.length===0){this._store.set({profile:{...this._store.state.profile,impact:null}});return}let s=++this._previewSeq;this._store.set({profile:{...this._store.state.profile,impacting:!0}});try{let l=await Ie(this.hass.connection,e.entryId,o.map(c=>Tt(c)),{[r]:t});if(s!==this._previewSeq)return;this._store.set({profile:{...this._store.state.profile,impact:l.items,impacting:!1}})}catch(l){s===this._previewSeq&&this._store.set({profile:{...this._store.state.profile,impacting:!1}}),me(l)||console.warn("MyHOME panel: the impact preview could not be read",b(l))}}async _retry(){await this._refresh(),this._store.state.connection!=="live"&&await this._listen()}_ensureSession(){let e=this._store.state.entryId;if(!e||!this.hass)return null;if(this._sessionClient&&this._sessionClient.entryId===e)return this._sessionClient;this._release(this._sessionClient);let t=new Fe({connection:this.hass.connection,entryId:e,onChange:r=>this._store.set({session:r})});return this._sessionClient=t,this._store.set({clientId:t.clientId,session:t.session}),t}async _readSession(){let e=this._ensureSession();if(!e)return;let t=await e.get();if(!t.ok){this._store.set({sessionError:t});return}if(!t.session||_e(t.session)){this._store.set({sessionError:null});return}let r=await e.attach(t.session.session_id);this._store.set({sessionError:r.ok?null:r})}_leaveSession(){let e=this._sessionClient;!e||!e.session||e.leave()}async _calibrate(e){if(this._store.set({wizardIntent:e,sessionError:null}),!e){this._navigate("/calibrate"),this._store.state.route.view==="calibrate"&&this._readSession();return}let t=this._ensureSession();if(this._openingSession=!0,this._navigate("/calibrate"),!t)return;let r=await t.start(e);this._store.set({sessionError:r.ok?null:r})}async _takeControl(){let e=this._ensureSession();if(!e)return;let t=await e.takeControl();this._store.set({sessionError:t.ok?null:t})}async _cancelSession(e){let t=this._ensureSession();if(!t)return;let r=e==="claim"?await t.claimAndCancel():await t.cancel({force:e==="force"});if(r.ok||!r.error){this._store.set({sessionError:null,wizardIntent:null});return}this._store.set({sessionError:{error:r.error,recovery:r.recovery,freedAt:r.freedAt}})}async _actSession(e,t){let r=this._ensureSession();if(!r)return;let o=await r.act(e,t);this._store.set({sessionError:o.ok?null:o})}async _stopSession(){let e=this._ensureSession();if(!e)return;let t=await e.stop();this._store.set({sessionError:t.ok?null:t})}async _saveSession(e){let t=this._ensureSession();if(!t)return;let r=await t.save(e);if(!r.ok){this._store.set({sessionError:r});return}this._store.set({sessionError:null,wizardIntent:null,...r.overview?{overview:r.overview}:{}})}async _endOther(){let e=this._ensureSession();if(!e)return;this._store.set({busy:{...this._store.state.busy,ask:null}});let t=await e.endOther();if(!t.ok){this._store.set({sessionError:t});return}t.overview&&this._store.setOverview(t.overview),this._store.set({busy:{ask:null,service:t.stillCalibrating},...t.stillCalibrating?{}:{sessionError:null}})}_renderView(){let e=this._store.state;if(e.status==="loading")return An(this._i18n);if(e.status==="error"||!e.overview){let r=e.error;return a`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(r?.translation_key,r?.translation_placeholders??{})}
        </div>
        <div class="soft">${r?`${r.code}: ${r.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._retry()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${N}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?a` · ${this._version}`:d}
        </div>
      </div>`}let t=e.route;return t.view==="calibrate"?this._renderWizard():t.view!=="overview"&&!V(t)?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):a`<myhome-overview
      .i18n=${this._i18n}
      .state=${e}
      .actions=${this._assignActions}
    ></myhome-overview>`}_renderWizard(){try{return a`<myhome-wizard
        .i18n=${this._i18n}
        .state=${this._store.state}
        .actions=${this._wizardActions}
        .hass=${this.hass??null}
      ></myhome-wizard>`}catch(e){return console.error("MyHOME panel: the guided calibration could not be drawn",e),a`<div class="card problem" role="alert">
        <div>${this._i18n.t("panel.wizard.render_error.title")}</div>
        <div class="soft">${this._i18n.t("panel.wizard.render_error.body")}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>this.requestUpdate()}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <button class="cta text" type="button" @click=${()=>{this._cancelSession("plain")}}>
            ${this._i18n.t("panel.wizard.action.end")}
          </button>
          <a href=${N}>${this._i18n.t("panel.common.action.configure")}</a>
        </div>
      </div>`}}_renderDrawer(){let e=this._store.state;if(!V(e.route)||e.status==="error")return d;let t=e.status==="loading"?Ze(this._i18n):e.route.view==="cover"?a`<myhome-cover-detail
              .i18n=${this._i18n}
              .state=${e}
              .actions=${this._detailActions}
            ></myhome-cover-detail>`:a`<myhome-profile-card
              .i18n=${this._i18n}
              .state=${e}
              .actions=${this._profileActions}
            ></myhome-profile-card>`;return xn({i18n:this._i18n,title:this._drawerTitle(),hasBack:this._drawerBack!==null,applying:e.applying,onClose:this._closeDrawer,content:t})}render(){let e=this._store.state,t=this._title(),r=e.route.view!=="overview";return a`
      <!--
        One named landmark for everything the panel draws, and deliberately not "main" or
        "banner": a custom panel is rendered inside Home Assistant's own document and the
        shell owns those. A region named by the page's own heading is a landmark a reader
        can jump to and one that cannot collide with the host's.
      -->
      <div class="page" role="region" aria-labelledby="panel-title">
        <div class="toolbar">
          ${this._renderMenuButton()}
          ${this._renderTitle(t)}
          ${this._renderGatewayPicker()} ${this._renderWizardExit()}
        </div>
      ${e.connection==="offline"?a`<div class="offline" role="status">
            ${this._i18n.t("panel.error.no_connection")}
          </div>`:d}
      <!--
        Not over the wizard: the banner's three offers are "go to the wizard", "end what is
        running" and "close the dialog", and on that route all three of them are already on
        the screen, with more to say about each than one strip can.
      -->
      ${e.overview&&e.route.view!=="calibrate"?Sn(this._i18n,e.overview,e.busy,this._bannerActions):d}
      <div class="content">
        ${Ge(e.announce)} ${this._renderView()}
        ${e.connection==="polling"&&e.status==="ready"?a`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:d}
      </div>
      ${this._renderDrawer()}
      <!--
        The overview draws its own five strips, because three of them are about a gesture
        it owns, and it stops drawing them while a drawer is over it. The routed cards
        have no gestures and two of the five still apply to them: a write in the air, and
        what it came to with "Annulla" beside it. So exactly one of the two is drawing
        strips at any moment, and they are drawn over the drawer (z-index 70) because a
        refusal of a write made *inside* the drawer has to be readable from there.
      -->
      ${r&&e.applying?Je(this._i18n):d}
      ${r&&e.snack&&!e.applying?et(this._i18n,e.snack.message,e.snack.undoToken?()=>{this._undo()}:null):d}
      </div>
    `}_renderTitle(e){let t=this._store.state,r=t.route.view==="calibrate"?vn(t.session??null,this._i18n):null;return r?a`<div class="titles">
      <h1 class="title" id="panel-title">${e}</h1>
      <p class="phase">${r}</p>
    </div>`:a`<h1 class="title" id="panel-title">${e}</h1>`}_renderWizardExit(){let e=this._store.state;return e.route.view!=="calibrate"||!e.session?d:a`<button
      type="button"
      data-wizard-exit
      aria-label=${this._i18n.t("panel.wizard.action.exit")}
      @click=${()=>this._store.set({wizardExit:!0})}
    >
      ✕
    </button>`}_renderGatewayPicker(){let e=this._store.state,t=e.overview?.entries??[],r=t.find(s=>s.entry_id===e.entryId);if(t.length<=1)return d;let o=this._i18n.t("panel.common.gateway",{gateway:r?.title??""});return a`<select
      class="gateway"
      aria-label=${o}
      .value=${e.entryId??""}
      ?disabled=${e.applying}
      @change=${s=>{this._switchGateway(s.target.value)}}
    >
      ${t.map(s=>a`<option value=${s.entry_id} ?selected=${s.entry_id===e.entryId}>
          ${s.title}
        </option>`)}
    </select>`}async _switchGateway(e){if(!e||e===this._store.state.entryId)return;let t=this._unsubscribeWs;this._unsubscribeWs=null,await t?.().catch(()=>{}),this._clearSnack();let r=this._sessionClient;this._sessionClient=null,this._release(r),this._store.set({...Ue,entryId:e,session:null,sessionError:null,wizardIntent:null,detail:xe,profile:$e,search:"",room:"",snack:null}),this._navigate("/"),await this._refresh(),await this._listen()}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",Qt);export{Qt as MyHomeCalibrationPanel};
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
