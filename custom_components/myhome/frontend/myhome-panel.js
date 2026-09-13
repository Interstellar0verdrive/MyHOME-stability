/* MyHOME calibration panel */
var B=globalThis,W=B.ShadowRoot&&(B.ShadyCSS===void 0||B.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ie=Symbol(),Ee=new WeakMap,L=class{constructor(t,e,r){if(this._$cssResult$=!0,r!==ie)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(W&&t===void 0){let r=e!==void 0&&e.length===1;r&&(t=Ee.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&Ee.set(e,t))}return t}toString(){return this.cssText}},Ce=n=>new L(typeof n=="string"?n:n+"",void 0,ie),m=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((r,o,i)=>r+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+n[i+1],n[0]);return new L(e,n,ie)},Te=(n,t)=>{if(W)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let r=document.createElement("style"),o=B.litNonce;o!==void 0&&r.setAttribute("nonce",o),r.textContent=e.cssText,n.appendChild(r)}},se=W?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let r of t.cssRules)e+=r.cssText;return Ce(e)})(n):n;var{is:Gt,defineProperty:Kt,getOwnPropertyDescriptor:Vt,getOwnPropertyNames:Xt,getOwnPropertySymbols:Yt,getPrototypeOf:Zt}=Object,j=globalThis,Ae=j.trustedTypes,Jt=Ae?Ae.emptyScript:"",Qt=j.reactiveElementPolyfillSupport,O=(n,t)=>n,ae={toAttribute(n,t){switch(t){case Boolean:n=n?Jt:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},Ie=(n,t)=>!Gt(n,t),Me={attribute:!0,type:String,converter:ae,reflect:!1,useDefault:!1,hasChanged:Ie};Symbol.metadata??=Symbol("metadata"),j.litPropertyMetadata??=new WeakMap;var _=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Me){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let r=Symbol(),o=this.getPropertyDescriptor(t,r,e);o!==void 0&&Kt(this.prototype,t,o)}}static getPropertyDescriptor(t,e,r){let{get:o,set:i}=Vt(this.prototype,t)??{get(){return this[e]},set(a){this[e]=a}};return{get:o,set(a){let p=o?.call(this);i?.call(this,a),this.requestUpdate(t,p,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Me}static _$Ei(){if(this.hasOwnProperty(O("elementProperties")))return;let t=Zt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(O("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(O("properties"))){let e=this.properties,r=[...Xt(e),...Yt(e)];for(let o of r)this.createProperty(o,e[o])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[r,o]of e)this.elementProperties.set(r,o)}this._$Eh=new Map;for(let[e,r]of this.elementProperties){let o=this._$Eu(e,r);o!==void 0&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let r=new Set(t.flat(1/0).reverse());for(let o of r)e.unshift(se(o))}else t!==void 0&&e.push(se(t));return e}static _$Eu(t,e){let r=e.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let r of e.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Te(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,r){this._$AK(t,r)}_$ET(t,e){let r=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,r);if(o!==void 0&&r.reflect===!0){let i=(r.converter?.toAttribute!==void 0?r.converter:ae).toAttribute(e,r.type);this._$Em=t,i==null?this.removeAttribute(o):this.setAttribute(o,i),this._$Em=null}}_$AK(t,e){let r=this.constructor,o=r._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let i=r.getPropertyOptions(o),a=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:ae;this._$Em=o;let p=a.fromAttribute(e,i.type);this[o]=p??this._$Ej?.get(o)??p,this._$Em=null}}requestUpdate(t,e,r,o=!1,i){if(t!==void 0){let a=this.constructor;if(o===!1&&(i=this[t]),r??=a.getPropertyOptions(t),!((r.hasChanged??Ie)(i,e)||r.useDefault&&r.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,r))))return;this.C(t,e,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:r,reflect:o,wrapped:i},a){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),i!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(e=void 0),this._$AL.set(t,e)),o===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[o,i]of this._$Ep)this[o]=i;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[o,i]of r){let{wrapped:a}=i,p=this[o];a!==!0||this._$AL.has(o)||p===void 0||this.C(o,void 0,i,p)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(e)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};_.elementStyles=[],_.shadowRootOptions={mode:"open"},_[O("elementProperties")]=new Map,_[O("finalized")]=new Map,Qt?.({ReactiveElement:_}),(j.reactiveElementVersions??=[]).push("2.1.2");var me=globalThis,Le=n=>n,G=me.trustedTypes,Oe=G?G.createPolicy("lit-html",{createHTML:n=>n}):void 0,qe="$lit$",b=`lit$${Math.random().toFixed(9).slice(2)}$`,Fe="?"+b,er=`<${Fe}>`,S=document,H=()=>S.createComment(""),D=n=>n===null||typeof n!="object"&&typeof n!="function",ge=Array.isArray,tr=n=>ge(n)||typeof n?.[Symbol.iterator]=="function",le=`[ 	
\f\r]`,z=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ze=/-->/g,He=/>/g,k=RegExp(`>|${le}(?:([^\\s"'>=/]+)(${le}*=${le}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),De=/'/g,Ne=/"/g,Be=/^(?:script|style|textarea|title)$/i,ve=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),s=ve(1),Tr=ve(2),Ar=ve(3),w=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Ue=new WeakMap,R=S.createTreeWalker(S,129);function We(n,t){if(!ge(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return Oe!==void 0?Oe.createHTML(t):t}var rr=(n,t)=>{let e=n.length-1,r=[],o,i=t===2?"<svg>":t===3?"<math>":"",a=z;for(let p=0;p<e;p++){let d=n[p],c,u,h=-1,g=0;for(;g<d.length&&(a.lastIndex=g,u=a.exec(d),u!==null);)g=a.lastIndex,a===z?u[1]==="!--"?a=ze:u[1]!==void 0?a=He:u[2]!==void 0?(Be.test(u[2])&&(o=RegExp("</"+u[2],"g")),a=k):u[3]!==void 0&&(a=k):a===k?u[0]===">"?(a=o??z,h=-1):u[1]===void 0?h=-2:(h=a.lastIndex-u[2].length,c=u[1],a=u[3]===void 0?k:u[3]==='"'?Ne:De):a===Ne||a===De?a=k:a===ze||a===He?a=z:(a=k,o=void 0);let v=a===k&&n[p+1].startsWith("/>")?" ":"";i+=a===z?d+er:h>=0?(r.push(c),d.slice(0,h)+qe+d.slice(h)+b+v):d+b+(h===-2?p:v)}return[We(n,i+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]},N=class n{constructor({strings:t,_$litType$:e},r){let o;this.parts=[];let i=0,a=0,p=t.length-1,d=this.parts,[c,u]=rr(t,e);if(this.el=n.createElement(c,r),R.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(o=R.nextNode())!==null&&d.length<p;){if(o.nodeType===1){if(o.hasAttributes())for(let h of o.getAttributeNames())if(h.endsWith(qe)){let g=u[a++],v=o.getAttribute(h).split(b),$=/([.?@])?(.*)/.exec(g);d.push({type:1,index:i,name:$[2],strings:v,ctor:$[1]==="."?de:$[1]==="?"?ce:$[1]==="@"?he:E}),o.removeAttribute(h)}else h.startsWith(b)&&(d.push({type:6,index:i}),o.removeAttribute(h));if(Be.test(o.tagName)){let h=o.textContent.split(b),g=h.length-1;if(g>0){o.textContent=G?G.emptyScript:"";for(let v=0;v<g;v++)o.append(h[v],H()),R.nextNode(),d.push({type:2,index:++i});o.append(h[g],H())}}}else if(o.nodeType===8)if(o.data===Fe)d.push({type:2,index:i});else{let h=-1;for(;(h=o.data.indexOf(b,h+1))!==-1;)d.push({type:7,index:i}),h+=b.length-1}i++}}static createElement(t,e){let r=S.createElement("template");return r.innerHTML=t,r}};function P(n,t,e=n,r){if(t===w)return t;let o=r!==void 0?e._$Co?.[r]:e._$Cl,i=D(t)?void 0:t._$litDirective$;return o?.constructor!==i&&(o?._$AO?.(!1),i===void 0?o=void 0:(o=new i(n),o._$AT(n,e,r)),r!==void 0?(e._$Co??=[])[r]=o:e._$Cl=o),o!==void 0&&(t=P(n,o._$AS(n,t.values),o,r)),t}var pe=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:r}=this._$AD,o=(t?.creationScope??S).importNode(e,!0);R.currentNode=o;let i=R.nextNode(),a=0,p=0,d=r[0];for(;d!==void 0;){if(a===d.index){let c;d.type===2?c=new U(i,i.nextSibling,this,t):d.type===1?c=new d.ctor(i,d.name,d.strings,this,t):d.type===6&&(c=new ue(i,this,t)),this._$AV.push(c),d=r[++p]}a!==d?.index&&(i=R.nextNode(),a++)}return R.currentNode=S,o}p(t){let e=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,e),e+=r.strings.length-2):r._$AI(t[e])),e++}},U=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,r,o){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=r,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=P(this,t,e),D(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==w&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):tr(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&D(this._$AH)?this._$AA.nextSibling.data=t:this.T(S.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:r}=t,o=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=N.createElement(We(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===o)this._$AH.p(e);else{let i=new pe(o,this),a=i.u(this.options);i.p(e),this.T(a),this._$AH=i}}_$AC(t){let e=Ue.get(t.strings);return e===void 0&&Ue.set(t.strings,e=new N(t)),e}k(t){ge(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,r,o=0;for(let i of t)o===e.length?e.push(r=new n(this.O(H()),this.O(H()),this,this.options)):r=e[o],r._$AI(i),o++;o<e.length&&(this._$AR(r&&r._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let r=Le(t).nextSibling;Le(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},E=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,r,o,i){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=i,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=l}_$AI(t,e=this,r,o){let i=this.strings,a=!1;if(i===void 0)t=P(this,t,e,0),a=!D(t)||t!==this._$AH&&t!==w,a&&(this._$AH=t);else{let p=t,d,c;for(t=i[0],d=0;d<i.length-1;d++)c=P(this,p[r+d],e,d),c===w&&(c=this._$AH[d]),a||=!D(c)||c!==this._$AH[d],c===l?t=l:t!==l&&(t+=(c??"")+i[d+1]),this._$AH[d]=c}a&&!o&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},de=class extends E{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},ce=class extends E{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},he=class extends E{constructor(t,e,r,o,i){super(t,e,r,o,i),this.type=5}_$AI(t,e=this){if((t=P(this,t,e,0)??l)===w)return;let r=this._$AH,o=t===l&&r!==l||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,i=t!==l&&(r===l||o);o&&this.element.removeEventListener(this.name,this,r),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},ue=class{constructor(t,e,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){P(this,t)}};var nr=me.litHtmlPolyfillSupport;nr?.(N,U),(me.litHtmlVersions??=[]).push("3.3.3");var je=(n,t,e)=>{let r=e?.renderBefore??t,o=r._$litPart$;if(o===void 0){let i=e?.renderBefore??null;r._$litPart$=o=new U(t.insertBefore(H(),i),i,void 0,e??{})}return o._$AI(n),o};var fe=globalThis,y=class extends _{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=je(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return w}};y._$litElement$=!0,y.finalized=!0,fe.litElementHydrateSupport?.({LitElement:y});var or=fe.litElementPolyfillSupport;or?.({LitElement:y});(fe.litElementVersions??=[]).push("4.2.2");var Ge={"panel.assign.action.discard_all":"Discard everything","panel.assign.action.review":"Review and confirm","panel.assign.action.review_hint":"Review and confirm the assignments","panel.assign.action.withdraw":"Withdraw this change","panel.assign.announce.applying":"The changes are being applied.","panel.assign.announce.armed":"Tap the destination group.","panel.assign.announce.discarded":"Every pending change has been discarded.","panel.assign.announce.drag_cancelled":"Drag cancelled.","panel.assign.announce.missing_travel":"Some covers have no travel.","panel.assign.announce.pending":"“{cover}” is pending, towards {target}. Nothing is written yet.","panel.assign.announce.reordered":"Order updated: it will be remembered.","panel.assign.announce.withdrawn":"“{cover}” goes back where it was: the change is withdrawn.","panel.assign.armed":"Tap the destination group for “{cover}”","panel.assign.drop_zone":"Take out of the profile — drop here","panel.assign.handle":"Move {cover} to another group, or reorder it","panel.assign.handle_hint":"Drag to assign or reorder, Enter to pick from a list","panel.assign.pending.all_own":"All values its own: nothing changes","panel.assign.pending.count":"{count} pending changes — nothing is written yet","panel.assign.pending.count_one":"1 pending change — nothing is written yet","panel.assign.pending.route":"{from} → {to}","panel.assign.pending.some_own":"Own values: those stay","panel.assign.target_none":"“No profile”","panel.assign.target_profile":"the profile “{profile}”","panel.banner.applying.body":"The covers are unavailable for a few seconds","panel.banner.applying.title":"The changes are being applied…","panel.banner.measuring.action.resume":"Resume the session","panel.banner.measuring.action.stop":"End it","panel.banner.measuring.body":"A guided calibration is using “{cover}”. Until the session ends, this panel only reads: nothing is written.","panel.banner.measuring.title":"Measurement in progress","panel.common.action.back":"Back","panel.common.action.cancel":"Cancel","panel.common.action.close":"Close","panel.common.action.configure":"Open Configure","panel.common.action.hide_all":"Hide the roll coefficients","panel.common.action.menu":"Open the Home Assistant menu","panel.common.action.retry":"Try again","panel.common.action.show_all":"Show every value, roll coefficients included","panel.common.all_rooms":"All rooms","panel.common.gateway":"Gateway {gateway}","panel.common.loading":"Loading…","panel.common.not_yet":"This screen arrives in a later version. Until then “Configure” does everything it will do.","panel.common.polling":"Live updates are not available on this version: the page refreshes on its own every 30 seconds.","panel.common.room_filter":"Filter by room","panel.common.search":"Search for a cover","panel.common.unit.centimetres":"cm","panel.detail.named":"Cover “{cover}”","panel.detail.unknown":"This gateway has no cover with that identifier.","panel.dialog.option.current":"current","panel.dialog.option.none":"No profile","panel.dialog.option.none_meta":"Values from the configuration file, or the defaults. The travel and the values of its own stay.","panel.dialog.option.profile":"Profile “{profile}”","panel.dialog.option.profile_meta":"{travel} cm · ascent {opening} s · descent {closing} s","panel.dialog.subtitle":"“{cover}” — the choice stays pending until it is confirmed.","panel.dialog.title":"Which profile?","panel.error.not_found":"The panel could not read this gateway.","panel.firstrun.action.measure":"Measure a cover","panel.firstrun.body":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.firstrun.how":"A profile is not written, it is measured. Pick one representative cover and measure it once, with the guided calibration: about three minutes. Similar covers can then follow it.","panel.firstrun.note":"This opens the Configure dialog: that is where the measuring happens. When it is done, the profile appears here.","panel.firstrun.title":"No profile yet","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.cover.from_file":"The configuration file assigns this profile: it is changed there, not here.","panel.overview.cover.origin_adjusted":"Adjusted","panel.overview.cover.origin_inherited":"Inherited","panel.overview.cover.profile_missing":"The profile “{profile}” is no longer defined: this cover is running on its own configuration.","panel.overview.cover.travel":"travel {travel} cm","panel.overview.cover.travel_needed":"travel to be entered","panel.overview.cover.travel_unknown":"travel not recorded","panel.overview.explanation":"A profile describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.overview.group.count":"{count} covers","panel.overview.group.count_one":"1 cover","panel.overview.group.empty":"No cover in this group.","panel.overview.group.from_file":"Defined in the configuration file, and read-only from here.","panel.overview.group.measured_on":"Measured on {cover} · {date}","panel.overview.group.measured_on_gone":"Measured on a cover this gateway no longer has · {date}","panel.overview.group.missing":"This profile is not defined any more: the covers below have quietly fallen back to their own configuration.","panel.overview.group.no_profile":"No profile","panel.overview.group.no_profile_note":"Values from the configuration file, or the defaults. It is not a fault: a cover with measurements of its own sits perfectly well here.","panel.overview.group.open":"Open the profile card","panel.overview.group.profile":"Profile “{profile}”","panel.overview.group.provenance_missing":"Where it was measured is not recorded.","panel.overview.group.values":"Reference travel {travel} cm · ascent {opening} s · descent {closing} s · slats {slat} s","panel.overview.group.values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.no_basic_covers":"Every cover of this gateway reports its own position, so there is no travel model to calibrate and nothing for this panel to do.","panel.overview.no_results":"No cover matches this search.","panel.overview.summary":"Profiles: {profiles} · Basic covers: {covers}","panel.overview.title":"Profiles and covers","panel.profile.name":"Profile “{profile}”","panel.profile.provenance_now_profile":"now follows “{profile}”","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.review.action.back":"Back to the overview","panel.review.action.confirm":"Confirm {count} assignments","panel.review.action.confirm_one":"Confirm 1 assignment","panel.review.action.missing_travel":"{count} travels missing","panel.review.action.missing_travel_one":"1 travel missing","panel.review.after":"After","panel.review.before":"Before","panel.review.intro":"The changes are written all at once. For each cover, this is what it will really use: the profile's values brought to its own travel.","panel.review.note.all_own":"It has values of its own for everything: nothing changes. The profile would only count for values removed later on.","panel.review.note.back_to_defaults":"The default values come back: the position in per cent will be a rough estimate. The travel and any value of its own stay.","panel.review.note.back_to_file":"The values of the configuration file come back. The travel and any value of its own stay.","panel.review.note.scaled":"Values of the profile “{profile}” (measured on {reference} cm) brought to a travel of {travel} cm.","panel.review.note.some_own":"It has some values of its own: those stay. Only the inherited values change.","panel.review.title":"Review and confirm","panel.review.travel.aria":"Curtain travel in centimetres","panel.review.travel.hint":"A profile is the measurement of one cover with a certain travel, and it is brought to the others in proportion. The travel of these is not known: measure the distance the bottom edge covers from fully closed to fully open, and write it in centimetres (decimals with a comma or with a point).","panel.review.travel.label":"Curtain travel","panel.review.travel.placeholder":"e.g. 145","panel.review.travel.required":"The travel is needed, in centimetres.","panel.review.travel.title":"How far does the curtain of these covers run?","panel.screen.completed":"Completed","panel.screen.motor":"Motor","panel.screen.new_text":"new text — not translated yet","panel.screen.not_in_this_version":"This step belongs to the guided calibration, which moves into the panel in a later version.","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.position":"Estimated position","panel.toast.action.undo":"Undo","panel.toast.assigned":"{count} assignments applied","panel.toast.assigned_one":"1 assignment applied","panel.toast.order_saved":"The new order will be remembered.","panel.toast.undone":"Changes undone: everything as it was."};var ye=Ge,Gr=Object.keys(ye);var sr="/myhome_static/",ar=/^!\[([^\]]*)\]\(([^)\s]+)\)$/;var K=n=>{let t=[];return n.split("**").forEach((r,o)=>{r&&t.push(o%2===1?s`<strong>${r}</strong>`:s`<span>${r}</span>`)}),t},lr=n=>/^\s*[-*]\s+/.test(n),C=n=>{let t=(n||"").replace(/\r\n/g,`
`).split(/\n{2,}/),e=[];for(let r of t){let o=r.trim();if(!o)continue;let i=ar.exec(o);if(i){e.push(i[2].startsWith(sr)?s`<img class="md-image" src=${i[2]} alt=${i[1]} />`:s`<p>${K(i[1])}</p>`);continue}let a=o.split(`
`);if(a.every(lr)){e.push(s`<ul>
          ${a.map(p=>s`<li>${K(p.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}e.push(s`<p>
        ${a.map((p,d)=>d===0?K(p):[s`<br />`,...K(p)])}
      </p>`)}return s`${e}`};var T=n=>n&&typeof n=="object"&&"code"in n?n:{code:"unknown_error",message:String(n)},Ke=(n,t)=>n.sendMessagePromise({type:"myhome/calibration/overview",...t?{entry_id:t}:{}}),Ve=(n,t)=>n.sendMessagePromise({type:"myhome/calibration/texts",language:t});var Xe=(n,t,e)=>n.sendMessagePromise({type:"myhome/calibration/preview",entry_id:t,items:e}),Ye=(n,t,e)=>n.subscribeMessage(e,{type:"myhome/calibration/subscribe",...t?{entry_id:t}:{}}),_e=n=>T(n).code==="unknown_command",Ze=(n,t,e,r)=>n.sendMessagePromise({type:"myhome/calibration/assign",entry_id:t,assignments:e,...r?{order:r}:{}}),Je=(n,t,e,r)=>n.sendMessagePromise({type:"myhome/calibration/reorder",entry_id:t,order:e,...r!==void 0?{profile:r}:{}});var Qe=(n,t,e)=>n.sendMessagePromise({type:"myhome/calibration/undo",entry_id:t,undo_token:e});var we=(n,t)=>{if(!t)return n;let e=n;for(let[r,o]of Object.entries(t))e=e.split(`{${r}}`).join(String(o));return e},x=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this.language="en";this.loaded=!1}async load(t,e){let r=await Ve(t,e);this._texts=r.texts??{},this.language=r.language,this.loaded=!0,this._numbers.clear(),this._dates=null}t(t,e){let r=this._lookup(t);if(r!==null)return we(r,e);let o=ye[t];return we(o??t,e)}md(t,e){return C(this.t(t,e))}refusal(t,e){let r=t?this._lookup(`exceptions.${t}.message`):null;return r!==null?we(r,e):this.t("panel.error.not_found")}origin(t,e){return this.t(`selector.calibration_origin.options.${t}`,{profile:e??""})}number(t,e){let r=this._numbers.get(e);return r||(r=new Intl.NumberFormat(this.language,{minimumFractionDigits:e,maximumFractionDigits:e}),this._numbers.set(e,r)),r.format(t)}date(t){let e=new Date(t);return Number.isNaN(e.getTime())?t:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(e))}_lookup(t){let e=this._texts;for(let r of t.split(".")){if(e===null||typeof e!="object")return null;e=e[r]}return typeof e=="string"?e:null}};var et=n=>typeof customElements<"u"&&customElements.get(n)!==void 0;var tt=n=>{n.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var be=(n,t)=>{let e=V(n.unique_id,t);return e?e.to:n.profile??null},V=(n,t)=>t.find(e=>e.cover===n),rt=(n,t,e)=>{let r=n.filter(o=>o.cover!==t.unique_id);return e===(t.profile??null)?{pending:r,withdrawn:!0}:{pending:[...r,{cover:t.unique_id,to:e}],withdrawn:!1}},nt=(n,t)=>{let e=new Map(n.covers.map(i=>[i.unique_id,i]));if(!t)return[...n.covers].sort((i,a)=>i.order_index-a.order_index);let r=new Set,o=[];for(let i of t){let a=e.get(i);a&&!r.has(i)&&(r.add(i),o.push(a))}for(let i of n.covers)r.has(i.unique_id)||o.push(i);return o},ot=(n,t,e)=>{let r=n.filter(i=>i!==t),o=r.length;if(e.beforeId){let i=r.indexOf(e.beforeId);o=i<0?r.length:i}else if(e.afterId){let i=r.indexOf(e.afterId);o=i<0?r.length:i+1}return[...r.slice(0,o),t,...r.slice(o)]},xe=(n,t)=>n.map(e=>{let r=t[e.cover],o=r===void 0?void 0:it(r);return{cover_unique_id:e.cover,profile:e.to,...o==null?{}:{height:o}}}),it=n=>{let t=n.trim().replace(",",".");if(!t)return null;let e=Number(t);return Number.isFinite(e)?e:null},pr=20,dr=500,q=n=>{if(n===void 0||n.trim()==="")return"missing_travel";let t=it(n);return t===null?"not_a_number":t<pr||t>dr?"out_of_range":null},st=(n,t)=>t.to!==null&&n.height===null,X=["opening_time","closing_time","slat_time","opening_roll","closing_roll"],$e=["opening_time","closing_time","slat_time"],at=["opening_roll","closing_roll"],ke={opening_time:1,closing_time:1,slat_time:1,opening_roll:2,closing_roll:2};var cr={view:"overview",params:{},path:"/"},lt=n=>{let t="/"+(n||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(t==="/")return cr;let e=t.slice(1).split("/"),r=e.slice(1).join("/"),o=r;try{o=decodeURIComponent(r)}catch{}return e[0]==="cover"&&r?{view:"cover",params:{id:o},path:t}:e[0]==="profile"&&r?{view:"profile",params:{name:o},path:t}:e[0]==="calibrate"&&r?{view:"calibrate",params:{session:o},path:t}:{view:"unknown",params:{},path:t}};var Y=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(t){this._onChange=t,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(t){let e=t||"/";if(e===this._fromHost)return;let r=this.current.path;this._fromHost=e,this.current.path!==r&&this._emit()}get current(){let t=typeof location<"u"?location.hash:"";return t&&t.length>1?lt(t.slice(1)):lt(this._fromHost)}navigate(t){let e="#"+(t.startsWith("/")?t:"/"+t);location.hash!==e&&(location.hash=e)}_emit(){this._onChange(this.current)}};var Re=n=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:n,search:"",room:"",announce:"",pending:[],order:null,drag:null,armed:null,dialog:null,review:!1,heights:{},heightsForced:!1,showAll:!1,preview:null,previewing:!1,applying:!1,snack:null,writeError:null}),Se={pending:[],order:null,heights:{},heightsForced:!1,preview:null,previewing:!1,review:!1,writeError:null},Z=class{constructor(t){this._subscribers=new Set;this._state=Re(t)}get state(){return this._state}subscribe(t){return this._subscribers.add(t),()=>this._subscribers.delete(t)}set(t){this._state={...this._state,...t};for(let e of this._subscribers)e(this._state)}setOverview(t){this.set({overview:t,entryId:t.entry_id,status:"ready",error:null})}setError(t){this.set({status:"error",error:t})}announce(t){this.set({announce:""}),this.set({announce:t})}};var A=m`
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
`,M=m`
  .card {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
  }
`,I=m`
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
`,J=m`
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
`,Q=m`
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
`;var dt=n=>s`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${n}</div>`,hr=n=>{requestAnimationFrame(()=>{let t=n();t&&t.focus()})};var ee=class{constructor(){this._root=null;this._onKey=t=>{if(t.key!=="Tab"||!this._root)return;let e=pt(this._root);if(e.length===0){t.preventDefault(),this._root.focus();return}let r=e[0],o=e[e.length-1],i=this._root.getRootNode().activeElement;t.shiftKey&&(i===r||i===this._root)?(t.preventDefault(),o.focus()):!t.shiftKey&&i===o&&(t.preventDefault(),r.focus())}}hold(t){this.release(),this._root=t,t.addEventListener("keydown",this._onKey),hr(()=>pt(t)[0]??t)}release(){this._root?.removeEventListener("keydown",this._onKey),this._root=null}},pt=n=>Array.from(n.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter(t=>t.offsetParent!==null||t===n);var ct=m`
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
`,ht=(n,t,e)=>s`<div class="measuring" role="status" aria-live="polite">
    <strong>${n.t("panel.banner.measuring.title")}</strong>
    <span class="body">${n.t("panel.banner.measuring.body",{cover:t})}</span>
    <span class="links">
      <a href=${e}>${n.t("panel.banner.measuring.action.resume")}</a>
      <a href=${e}>${n.t("panel.banner.measuring.action.stop")}</a>
    </span>
  </div>`;var ut=n=>{let t=new Map;for(let e of n.querySelectorAll("[data-row]")){let r=e.getBoundingClientRect();t.set(e.getAttribute("data-row")??"",{top:r.top,left:r.left})}return t},mt=(n,t)=>{if(!ur())for(let e of n.querySelectorAll("[data-row]")){let r=t.get(e.getAttribute("data-row")??"");if(!r)continue;let o=e.getBoundingClientRect(),i=r.left-o.left,a=r.top-o.top;if(Math.abs(i)<1&&Math.abs(a)<1)continue;e.style.transition="none",e.style.transform=`translate(${i}px, ${a}px)`,e.offsetHeight,e.style.transition="transform 220ms ease",e.style.transform="";let p=()=>{e.style.transition="",e.removeEventListener("transitionend",p)};e.addEventListener("transitionend",p)}},ur=()=>typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches;var te=class{constructor(t){this._start=null;this._longPress=null;this._ghost=null;this._target=null;this._scroll=null;this._edge=0;this._scroller=null;this._clearLongPressOnce=()=>this._clearLongPress();this._onMove=t=>{let e=this._start;if(!e)return;if(!e.live){if(Math.hypot(t.clientX-e.x,t.clientY-e.y)<6)return;e.live=!0,this._callbacks.onStart(e.cover)}this._moveGhost(t.clientX,t.clientY),this._autoScroll(t.clientX,t.clientY);let r=this._targetAt(t.clientX,t.clientY,e.cover);mr(r,this._target)||(this._target=r,this._callbacks.onOver(r))};this._onUp=()=>this._finish(!0);this._onCancel=()=>this._finish(!1);this._callbacks=t}get dragging(){return this._start?.live?this._start.cover:null}press(t,e){if(!this._callbacks.blocked()){if(this._callbacks.narrow()){this._arm(t);return}e.preventDefault(),this._start={cover:t,x:e.clientX,y:e.clientY,live:!1},window.addEventListener("pointermove",this._onMove),window.addEventListener("pointerup",this._onUp),window.addEventListener("pointercancel",this._onCancel)}}arm(t){this._callbacks.blocked()||this._arm(t)}cancel(){if(this._start?.live){this._finish(!1);return}this._clear()}stop(){this._clear(),this._clearLongPress()}_arm(t){this._clearLongPress(),this._longPress=setTimeout(()=>{this._longPress=null,this._callbacks.onArm(t)},450),window.addEventListener("pointerup",this._clearLongPressOnce),window.addEventListener("pointermove",this._clearLongPressOnce),window.addEventListener("pointercancel",this._clearLongPressOnce)}_clearLongPress(){this._longPress&&(clearTimeout(this._longPress),this._longPress=null),window.removeEventListener("pointerup",this._clearLongPressOnce),window.removeEventListener("pointermove",this._clearLongPressOnce),window.removeEventListener("pointercancel",this._clearLongPressOnce)}_finish(t){let e=this._start?.live??!1;this._clear(),e&&this._callbacks.onEnd(t)}_clear(){window.removeEventListener("pointermove",this._onMove),window.removeEventListener("pointerup",this._onUp),window.removeEventListener("pointercancel",this._onCancel),this._start=null,this._target=null,this._stopScrolling(),this._ghost?.remove(),this._ghost=null}ghost(t,e){let r=document.createElement("div");r.className="drag-ghost",r.setAttribute("aria-hidden","true"),r.textContent=t,e.appendChild(r),this._ghost=r}_moveGhost(t,e){this._ghost&&(this._ghost.style.transform=`translate(${t+12}px, ${e+8}px)`)}_autoScroll(t,e){let r=this._callbacks.root().querySelector(".groups");if(!r||r.scrollWidth<=r.clientWidth){this._stopScrolling();return}let o=r.getBoundingClientRect(),i=t<o.left+64?-1:t>o.right-64?1:0;if(this._edge=i,this._scroller=r,i===0){this._stopScrolling();return}if(this._scroll===null){let a=()=>{this._edge===0||!this._scroller||(this._scroller.scrollLeft+=this._edge*14,this._scroll=requestAnimationFrame(a))};this._scroll=requestAnimationFrame(a)}}_stopScrolling(){this._edge=0,this._scroll!==null&&(cancelAnimationFrame(this._scroll),this._scroll=null)}_targetAt(t,e,r){let o=this._callbacks.root().elementFromPoint(t,e),i=o?.closest?.("[data-group]");if(!i)return null;let a=i.getAttribute("data-group")??"",p=o?.closest?.("[data-row]"),d=p?.getAttribute("data-row")??null;if(!p||!d||d===r)return{group:a,beforeId:null,afterId:null,end:!0};let c=p.getBoundingClientRect();return e<c.top+c.height/2?{group:a,beforeId:d,afterId:null,end:!1}:{group:a,beforeId:null,afterId:d,end:!1}}},mr=(n,t)=>n===null||t===null?n===t:n.group===t.group&&n.beforeId===t.beforeId&&n.afterId===t.afterId;var gt=m`
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
`,vt=(n,t,e,r)=>{let o=t==="measured"?"measured":t==="adjusted"?"adjusted":"neutral",i;return r&&t==="inherited"?i=n.t("panel.overview.cover.origin_inherited"):r&&t==="adjusted"?i=n.t("panel.overview.cover.origin_adjusted"):i=n.origin(t,e),s`<span class="chip ${o}"
    >${o==="adjusted"?s`<span class="dot" aria-hidden="true"></span>`:l}${i}</span
  >`};var ft=m`
  .row {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px;
    border-radius: 8px;
    min-height: 48px;
    -webkit-user-select: none;
    -webkit-touch-callout: none;
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

  /* The insertion line takes the divider's place while a row is in flight. */
  .row .insert-line {
    position: absolute;
    left: 8px;
    right: 8px;
    top: -2px;
    height: 3px;
    border-radius: 2px;
    background: var(--myhome-primary);
    pointer-events: none;
  }

  .row .pending-outline {
    position: absolute;
    inset: 0;
    border: 2px dashed var(--myhome-primary);
    border-radius: 8px;
    pointer-events: none;
  }

  .row .source-veil {
    position: absolute;
    inset: 0;
    background: var(--myhome-background-soft);
    opacity: 0.7;
    border-radius: 8px;
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

  /* The pending chip: the route this shutter is on, and the way to take it back. */
  .route {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-size: 12px;
    color: var(--myhome-primary);
    background: var(--myhome-primary-faint);
    border: 1px dashed var(--myhome-primary);
    border-radius: 10px;
    padding: 2px 2px 2px 8px;
    max-width: 100%;
  }

  .route .text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /*
   * 20 px of ink inside a 48 px target: the design fixes the little cross at 20 px, and
   * the handoff's minimum target at 48. Negative margins keep the chip the height it is
   * drawn at while the hit area reaches the row's edges.
   */
  .route .withdraw {
    width: 48px;
    height: 48px;
    margin: -14px -14px -14px 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    border-radius: 24px;
  }

  .row .note {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-info);
    margin-top: 4px;
  }
`,gr=(n,t,e)=>{let r=t.height!==null?n.t("panel.overview.cover.travel",{travel:n.number(t.height,0)}):e?n.t("panel.overview.cover.travel_needed"):n.t("panel.overview.cover.travel_unknown");return t.area?`${t.area} · ${r}`:r},vr=(n,t)=>t.has_own.length===0?"":X.every(e=>t.has_own.includes(e))?n.t("panel.assign.pending.all_own"):n.t("panel.assign.pending.some_own"),yt=(n,t)=>{let{i18n:e,pending:r}=t,o=!!r&&r.to!==null&&n.height===null,i=r?vr(e,n):"";return s`<div class="row" data-row=${n.unique_id}>
    ${t.insertBefore?s`<div class="insert-line" aria-hidden="true"></div>`:t.first?l:s`<div class="divider" aria-hidden="true"></div>`}
    ${r?s`<div class="pending-outline" aria-hidden="true"></div>`:l}
    ${t.dragging?s`<div class="source-veil" aria-hidden="true"></div>`:l}
    <button
      class="handle"
      type="button"
      ?disabled=${t.locked}
      aria-label=${e.t("panel.assign.handle",{cover:n.name})}
      title=${t.locked?e.t("panel.banner.measuring.title"):e.t("panel.assign.handle_hint")}
      @pointerdown=${a=>t.onGrab(n,a)}
      @click=${a=>a.stopPropagation()}
      @keydown=${a=>{(a.key==="Enter"||a.key===" ")&&(a.preventDefault(),t.locked||t.onPick(n))}}
    >
      ⠿
    </button>
    <button
      class="main"
      type="button"
      title=${n.name}
      @click=${()=>t.onOpen(n)}
      @pointerdown=${()=>t.onRowPress(n)}
    >
      <span class="name">${n.name}</span>
      <span class="sub">${gr(e,n,o)}</span>
      <span class="chips">
        ${vt(e,n.origin,n.profile,t.short)}
        ${r?s`<span class="route">
              <span class="text">${t.route}</span>
              <span
                class="withdraw"
                role="button"
                tabindex="0"
                aria-label=${e.t("panel.assign.action.withdraw")}
                title=${e.t("panel.assign.action.withdraw")}
                @click=${a=>{a.stopPropagation(),t.onWithdraw(n)}}
                @keydown=${a=>{(a.key==="Enter"||a.key===" ")&&(a.preventDefault(),a.stopPropagation(),t.onWithdraw(n))}}
                >✕</span
              >
            </span>`:l}
      </span>
      ${i?s`<span class="note">${i}</span>`:l}
      ${n.profile_missing?s`<span class="warn"
            >${e.t("panel.overview.cover.profile_missing",{profile:n.profile??""})}</span
          >`:l}
      ${n.profile_from_file&&!n.profile_missing?s`<span class="sub">${e.t("panel.overview.cover.from_file")}</span>`:l}
    </button>
  </div>`};var _t=m`
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 60;
  }

  .dialog {
    position: fixed;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: min(440px, 92vw);
    max-height: 80vh;
    overflow: auto;
    background: var(--myhome-card);
    color: var(--myhome-text);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    z-index: 61;
    padding: 20px;
    box-sizing: border-box;
  }

  .dialog h2 {
    margin: 0 0 4px;
    font-size: 18px;
    font-weight: 500;
  }

  .dialog .subtitle {
    margin: 0 0 16px;
    font-size: 13.5px;
    color: var(--myhome-text-soft);
  }

  .dialog .options {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /*
   * The selected option is a 1 px border plus an inset ring of the same colour, not a
   * 2 px border: the ring is drawn inside the element, so the option does not grow when it
   * becomes the current one and the list does not shuffle under the pointer.
   */
  .dialog .option {
    text-align: left;
    border-radius: 8px;
    font: inherit;
    padding: 12px;
    min-height: 48px;
    cursor: pointer;
    border: 1px solid var(--myhome-divider);
    background: transparent;
    color: inherit;
  }

  .dialog .option.current {
    border-color: var(--myhome-primary);
    box-shadow: inset 0 0 0 1px var(--myhome-primary);
    background: var(--myhome-primary-faint);
  }

  .dialog .option .line {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .dialog .option .title {
    font-weight: 500;
    flex: 1;
  }

  .dialog .option .tag {
    font-size: 12.5px;
    color: var(--myhome-primary);
  }

  .dialog .option .meta {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    margin-top: 2px;
  }

  .dialog .foot {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

  .dialog .foot button {
    min-height: 44px;
    padding: 0 16px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    font: inherit;
    font-size: 14px;
    cursor: pointer;
  }
`,fr=(n,t)=>t.missing||t.values.opening_time===void 0?n.t("panel.overview.group.values_unknown"):n.t("panel.dialog.option.profile_meta",{travel:t.reference_height===null?"?":n.number(t.reference_height,0),opening:n.number(t.values.opening_time,1),closing:n.number(t.values.closing_time,1)}),wt=n=>{let{i18n:t}=n,e=(r,o,i)=>s`<button
    class="option ${n.current===r?"current":""}"
    type="button"
    aria-current=${n.current===r?"true":l}
    @click=${()=>n.onPick(r)}
  >
    <span class="line"
      ><span class="title">${o}</span
      >${n.current===r?s`<span class="tag">${t.t("panel.dialog.option.current")}</span>`:l}</span
    >
    <span class="meta">${i}</span>
  </button>`;return s`
    <div class="backdrop" aria-hidden="true" @click=${n.onClose}></div>
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      data-focus-root
    >
      <h2 id="dialog-title">${t.t("panel.dialog.title")}</h2>
      <p class="subtitle">
        ${t.t("panel.dialog.subtitle",{cover:n.cover.name})}
      </p>
      <div class="options">
        ${n.profiles.map(r=>e(r.name,t.t("panel.dialog.option.profile",{profile:r.name}),fr(t,r)))}
        ${e(null,t.t("panel.dialog.option.none"),t.t("panel.dialog.option.none_meta"))}
      </div>
      <div class="foot">
        <button type="button" @click=${n.onClose}>
          ${t.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `};var bt=m`
  .groups {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /*
   * From 600 px the groups stand side by side and the row of them scrolls sideways, which
   * is what makes a drag between two profiles one gesture. Below it they stack, and the
   * gesture is press-and-tap instead.
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
      /* A drag near the edge scrolls this; the browser must not fight it with inertia. */
      overscroll-behavior-x: contain;
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

  /* A drop at the end of the group: the insertion line under the last row. */
  .group-body .insert-end {
    margin: 0 8px;
    height: 3px;
    border-radius: 2px;
    background: var(--myhome-primary);
    pointer-events: none;
  }

  /*
   * The two outlines. Solid means "let go and it lands here"; dashed means "this is a
   * target you can tap". Both are overlays and not borders, so the card does not change
   * size and the whole row of groups does not shift the moment a drag begins.
   */
  .group .over,
  .group .armed-target {
    position: absolute;
    inset: 0;
    border-radius: var(--myhome-radius);
    pointer-events: none;
  }

  .group .over {
    border: 2px solid var(--myhome-primary);
  }

  .group .armed-target {
    border: 2px dashed var(--myhome-primary);
  }

  /* Collapsed: the card is its own heading, and the heading is the target. */
  .group.collapsed .group-head {
    border-bottom: none;
    min-height: 48px;
    cursor: pointer;
  }
`,xt=(n,t)=>{let{i18n:e}=t,r=n.covers.length===1?e.t("panel.overview.group.count_one"):e.t("panel.overview.group.count",{count:n.covers.length}),o=t.collapsed;return s`<section
    class="group ${o?"collapsed":""}"
    data-group=${n.key??"none"}
    aria-labelledby=${n.id}
  >
    <div
      class="group-head"
      @click=${()=>{o&&t.onTarget(n.key)}}
    >
      <div class="line">
        <h2 id=${n.id}>
          ${n.key===null?n.title:s`<button
                type="button"
                title=${o?e.t("panel.assign.armed",{cover:""}):e.t("panel.overview.group.open")}
                @click=${i=>{if(i.stopPropagation(),o){t.onTarget(n.key);return}t.onOpenProfile(n.key)}}
              >
                ${n.title}
              </button>`}
        </h2>
        <span class="count">${r}</span>
      </div>
      ${n.values&&!o?s`<p class="meta">${n.values}</p>`:l}
      ${o?l:n.warning?s`<p class="meta second warn">${n.warning}</p>`:n.provenance?s`<p class="meta second">${n.provenance}</p>`:l}
    </div>
    ${o?l:s`<div class="group-body">
          ${n.covers.map((i,a)=>yt(i,{i18n:e,short:i.profile===n.key,first:a===0,pending:t.pending.find(p=>p.cover===i.unique_id),route:t.route(i),locked:t.locked,insertBefore:t.insertBefore===i.unique_id,dragging:t.dragging===i.unique_id,onOpen:t.onOpenCover,onGrab:t.onGrab,onRowPress:t.onRowPress,onPick:t.onPick,onWithdraw:t.onWithdraw}))}
          ${t.insertEnd?s`<div class="insert-end" aria-hidden="true"></div>`:l}
          ${n.covers.length===0?s`<p class="empty">${e.t("panel.overview.group.empty")}</p>`:l}
        </div>`}
    ${t.over?s`<div class="over" aria-hidden="true"></div>`:l}
    ${o?s`<div class="armed-target" aria-hidden="true"></div>`:l}
  </section>`};var kt=m`
  .sheet-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 50;
  }

  /* The phone: a sheet from the bottom, never taller than 86 vh. */
  .sheet {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    max-height: 86vh;
    background: var(--myhome-card);
    color: var(--myhome-text);
    z-index: 51;
    border-radius: 16px 16px 0 0;
    box-shadow: var(--myhome-shadow);
    display: flex;
    flex-direction: column;
  }

  /* From 600 px, a panel from the right instead. */
  @media (min-width: 600px) {
    .sheet {
      top: 0;
      left: auto;
      right: 0;
      bottom: 0;
      width: min(480px, 100vw);
      max-height: none;
      border-radius: 0;
    }
  }

  .sheet .head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--myhome-divider);
  }

  .sheet .head h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 500;
    flex: 1;
  }

  .sheet .head button {
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    font-size: 20px;
    cursor: pointer;
    border-radius: 24px;
  }

  .sheet .body {
    flex: 1;
    overflow: auto;
    padding: 16px;
  }

  .sheet .intro {
    margin: 0 0 16px;
    font-size: 13.5px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .sheet .travel-note {
    background: var(--myhome-info-pastel);
    border-radius: 8px;
    padding: 12px;
    margin: 0 0 16px;
    font-size: 13.5px;
    line-height: 1.5;
  }

  .sheet .travel-note strong {
    font-weight: 500;
    display: block;
    margin-bottom: 4px;
  }

  .sheet .item {
    border: 1px solid var(--myhome-divider);
    border-radius: 8px;
    padding: 12px;
    margin: 0 0 12px;
  }

  .sheet .item .line {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }

  .sheet .item .name {
    font-weight: 500;
    flex: 1 1 auto;
    min-width: 0;
  }

  .sheet .item .route {
    font-size: 13px;
    color: var(--myhome-text-soft);
  }

  .sheet label.travel {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 10px 0 2px;
    font-size: 13.5px;
  }

  .sheet label.travel .what {
    flex: 1;
  }

  .sheet label.travel input {
    width: 96px;
    height: 44px;
    border-radius: 8px;
    border: 1px solid var(--myhome-divider);
    background: var(--myhome-card);
    color: inherit;
    padding: 0 10px;
    font: inherit;
    font-size: 14px;
    text-align: right;
  }

  .sheet label.travel input[aria-invalid="true"] {
    border-color: var(--myhome-error);
  }

  .sheet .field-error {
    margin: 2px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error);
    text-align: right;
  }

  .sheet table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 0;
    font-size: 13.5px;
  }

  .sheet th {
    font-weight: 400;
    color: var(--myhome-text-soft);
    padding: 4px 0;
    border-bottom: 1px solid var(--myhome-divider);
    text-align: right;
  }

  .sheet th.what {
    text-align: left;
  }

  .sheet th.after {
    font-weight: 500;
    color: var(--myhome-text);
  }

  .sheet td {
    padding: 5px 0;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .sheet td.what {
    text-align: left;
    color: var(--myhome-text-soft);
  }

  .sheet td.after {
    font-weight: 500;
  }

  .sheet .note {
    margin: 10px 0 0;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .sheet .problem {
    margin: 10px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error);
    line-height: 1.5;
  }

  .sheet .show-all {
    border: none;
    background: transparent;
    color: var(--myhome-primary);
    font: inherit;
    font-size: 13.5px;
    cursor: pointer;
    padding: 4px 0;
    min-height: 44px;
  }

  .sheet .refusal {
    background: var(--myhome-error-pastel);
    border-radius: 8px;
    padding: 12px;
    margin: 0 0 12px;
    font-size: 13.5px;
    line-height: 1.5;
  }

  .sheet .foot {
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
    border-top: 1px solid var(--myhome-divider);
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }

  .sheet .foot button {
    min-height: 44px;
    border: none;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
  }

  .sheet .foot .back {
    padding: 0 16px;
    background: transparent;
    color: var(--myhome-text-soft);
  }

  .sheet .foot .confirm {
    padding: 0 24px;
    border-radius: 22px;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    font-weight: 500;
  }

  .sheet .foot .confirm[disabled] {
    background: var(--myhome-background-soft);
    color: var(--myhome-text-off);
    cursor: default;
  }
`,yr=(n,t,e,r,o)=>{if(X.every(a=>t.has_own.includes(a)))return n.t("panel.review.note.all_own");if(t.has_own.length>0)return n.t("panel.review.note.some_own");if(e.to===null)return r?.origin==="from_the_file"?n.t("panel.review.note.back_to_file"):n.t("panel.review.note.back_to_defaults");let i=o.get(e.to);return!r||r.height===null||!i||i.reference_height===null?"":n.t("panel.review.note.scaled",{profile:e.to,reference:n.number(i.reference_height,0),travel:n.number(r.height,0)})},$t=(n,t,e,r)=>n.refusal(e,{cover:t.name,covers:t.name,count:1,profile:r.to??"",key:n.t("panel.review.travel.label"),min:20,max:500}),Rt=n=>{let{i18n:t}=n,e=new Map((n.preview??[]).map(p=>[p.cover_unique_id,p])),r=n.pending.map(p=>({change:p,cover:n.covers.get(p.cover)})).filter(p=>p.cover!==void 0),o=r.filter(({change:p,cover:d})=>p.to!==null&&d.height===null&&q(n.heights[p.cover])!==null).length,i=n.showAll?[...$e,...at]:$e,a=p=>t.t(`options.step.calibration_edit.data.${p}`);return s`
    <div class="sheet-backdrop" aria-hidden="true" @click=${n.onClose}></div>
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
          @click=${n.onClose}
        >
          ✕
        </button>
      </div>
      <div class="body">
        <p class="intro">${t.t("panel.review.intro")}</p>
        ${n.refusal?s`<div class="refusal" role="alert">${n.refusal}</div>`:l}
        ${o>0?s`<div class="travel-note">
              <strong>${t.t("panel.review.travel.title")}</strong>
              ${t.t("panel.review.travel.hint")}
            </div>`:l}
        ${r.map(({change:p,cover:d})=>{let c=e.get(p.cover),u=n.heights[p.cover],h=p.to!==null&&d.height===null,g=h?q(u):null,v=g!==null&&(n.forced||(u??"")!==""),$=c&&c.problem===null?i.filter(f=>c.values[f]!==void 0&&d.values[f]!==void 0):[];return s`<section class="item">
            <div class="line">
              <span class="name">${d.name}</span>
              <span class="route">${n.route(d)}</span>
            </div>
            ${h?s`<label class="travel">
                    <span class="what">${t.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${u??""}
                      ?disabled=${n.applying}
                      aria-label=${t.t("panel.review.travel.aria")}
                      aria-invalid=${v?"true":"false"}
                      placeholder=${t.t("panel.review.travel.placeholder")}
                      @input=${f=>n.onHeight(p.cover,f.target.value)}
                    />
                    <span>${t.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${v?s`<p class="field-error">
                        ${g==="missing_travel"?t.t("panel.review.travel.required"):$t(t,d,g,p)}
                      </p>`:l}`:l}
            ${c&&c.problem!==null&&c.problem!=="missing_travel"?s`<p class="problem">
                  ${$t(t,d,c.problem,p)}
                </p>`:l}
            ${$.length>0?s`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${t.t("panel.review.before")}</th>
                      <th class="after">${t.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${$.map(f=>s`<tr>
                        <td class="what">${a(f)}</td>
                        <td>${t.number(d.values[f],ke[f]??1)}</td>
                        <td class="after">
                          ${t.number(c.values[f],ke[f]??1)}
                        </td>
                      </tr>`)}
                  </tbody>
                </table>`:l}
            ${(()=>{let f=yr(t,d,p,c,n.profiles);return f?s`<p class="note">${f}</p>`:l})()}
          </section>`})}
        <button class="show-all" type="button" @click=${n.onToggleShowAll}>
          ${n.showAll?t.t("panel.common.action.hide_all"):t.t("panel.common.action.show_all")}
        </button>
      </div>
      <div class="foot">
        <button class="back" type="button" ?disabled=${n.applying} @click=${n.onClose}>
          ${t.t("panel.review.action.back")}
        </button>
        <button
          class="confirm"
          type="button"
          ?disabled=${n.applying||n.forced&&o>0}
          @click=${n.onConfirm}
        >
          ${n.applying?t.t("panel.banner.applying.title"):o>0?o===1?t.t("panel.review.action.missing_travel_one"):t.t("panel.review.action.missing_travel",{count:o}):r.length===1?t.t("panel.review.action.confirm_one"):t.t("panel.review.action.confirm",{count:r.length})}
        </button>
      </div>
    </aside>
  `};var St=m`
  .strip {
    position: fixed;
    left: 50%;
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    transform: translateX(-50%);
    max-width: 92vw;
    box-sizing: border-box;
    box-shadow: var(--myhome-shadow);
  }

  .drop-zone {
    z-index: 45;
    padding: 14px 28px;
    min-height: 48px;
    display: flex;
    align-items: center;
    border-radius: 24px;
    font-size: 14px;
    font-weight: 500;
    border: 2px dashed var(--myhome-divider);
    background: var(--myhome-card);
    color: var(--myhome-text-soft);
  }

  .drop-zone.over {
    border: 2px solid var(--myhome-primary);
    color: var(--myhome-primary);
  }

  .dark {
    background: var(--myhome-text);
    color: var(--myhome-background);
    border-radius: 8px;
    font-size: 14px;
  }

  .armed {
    z-index: 40;
    bottom: calc(84px + env(safe-area-inset-bottom, 0px));
    padding: 10px 16px;
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .applying {
    z-index: 70;
    padding: 12px 20px;
  }

  .applying .under {
    display: block;
    font-size: 12px;
    opacity: 0.75;
    margin-top: 2px;
  }

  .snack {
    z-index: 70;
    padding: 8px 8px 8px 20px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dark button {
    min-height: 44px;
    padding: 0 12px;
    border: none;
    background: transparent;
    color: var(--myhome-snack-action);
    font: inherit;
    font-weight: 500;
    cursor: pointer;
  }

  .pending-bar {
    z-index: 30;
    background: var(--myhome-card);
    border: 1px solid var(--myhome-divider);
    border-radius: 28px;
    padding: 8px 8px 8px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .pending-bar .count {
    font-size: 14px;
  }

  .pending-bar .locked {
    font-size: 13px;
    color: var(--myhome-warning);
    flex-basis: 100%;
  }

  .pending-bar button {
    min-height: 44px;
    border: none;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
  }

  .pending-bar .discard {
    padding: 0 12px;
    background: transparent;
    color: var(--myhome-text-soft);
  }

  .pending-bar .review {
    padding: 0 20px;
    border-radius: 22px;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    font-weight: 500;
  }

  .pending-bar button[disabled] {
    color: var(--myhome-text-off);
    background: var(--myhome-background-soft);
    cursor: default;
  }

  /*
   * On a phone the pill is the width of the screen instead of the width of its longest
   * line: centred and shrink-to-fit, the count wraps onto three short lines and the two
   * buttons end up under each other in a column narrower than the cards behind it.
   */
  @media (max-width: 599px) {
    .strip.pending-bar {
      left: 8px;
      right: 8px;
      transform: none;
      max-width: none;
      justify-content: space-between;
    }

    .strip.pending-bar .count {
      flex-basis: 100%;
    }
  }
`,Pt=(n,t)=>s`<div class="strip drop-zone ${t?"over":""}" data-group="none">
    ${n.t("panel.assign.drop_zone")}
  </div>`,Et=(n,t,e)=>s`<div class="strip dark armed" role="status">
    <span>${n.t("panel.assign.armed",{cover:t})}</span>
    <button type="button" @click=${e}>${n.t("panel.common.action.cancel")}</button>
  </div>`,Ct=n=>{let{i18n:t}=n;return s`<div class="strip pending-bar">
    <span class="count"
      >${n.count===1?t.t("panel.assign.pending.count_one"):t.t("panel.assign.pending.count",{count:n.count})}</span
    >
    <button class="discard" type="button" @click=${n.onDiscard}>
      ${t.t("panel.assign.action.discard_all")}
    </button>
    <button
      class="review"
      type="button"
      ?disabled=${n.locked}
      title=${t.t("panel.assign.action.review_hint")}
      @click=${n.onReview}
    >
      ${t.t("panel.assign.action.review")}
    </button>
    ${n.locked?s`<span class="locked"
          >${t.t("panel.banner.measuring.body",{cover:n.lockedCover})}</span
        >`:l}
  </div>`},Tt=n=>s`<div class="strip dark applying" role="status">
    ${n.t("panel.banner.applying.title")}
    <span class="under">${n.t("panel.banner.applying.body")}</span>
  </div>`,At=(n,t,e)=>s`<div class="strip dark snack" role="status">
    <span>${t}</span>
    ${e?s`<button type="button" @click=${e}>
          ${n.t("panel.toast.action.undo")}
        </button>`:l}
  </div>`;var F="/config/integrations/integration/myhome",re=class extends y{constructor(){super();this._trap=new ee;this._returnTo=null;this._onKey=e=>{if(e.key==="Escape"){if(this.state.drag){this._drag.cancel();return}if(this.state.armed){this.actions.arm(null);return}if(this.state.dialog){this.actions.dialog(null);return}this.state.review&&!this.state.applying&&this.actions.review(!1)}};this._flip=null;this._route=e=>{let r=V(e.unique_id,this.state.pending);return r?this.i18n.t("panel.assign.pending.route",{from:this._groupName(e.profile??null),to:this._groupName(r.to)}):""};this._onGrab=(e,r)=>{this._drag.press(e.unique_id,r)};this._onRowPress=e=>{this._narrow&&!this._locked&&this._drag.arm(e.unique_id)};this.i18n=new x,this.state=Re({view:"overview",params:{},path:"/"}),this.actions={},this._drag=new te({root:()=>this.renderRoot,blocked:()=>this._locked,narrow:()=>this._narrow,onArm:e=>{let r=this._cover(e);r&&this.actions.arm(r)},onStart:e=>{let r=this._cover(e);r&&(this._drag.ghost(r.name,this.renderRoot),this.actions.drag(r))},onOver:e=>this.actions.over(e),onEnd:e=>this._endDrag(e)})}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[A,M,I,J,gt,ft,bt,St,_t,kt,m`
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
       *
       * The prototype drew the replacement as an SVG data URI with a fixed grey painted
       * into it. A data URI cannot read a CSS variable, so that grey would be the one
       * literal colour in the panel and the same grey in both themes - which is the thing
       * the handoff's first rule forbids. The chevron here is two borders on a wrapper's
       * pseudo-element instead, in the theme's own secondary text colour.
       */
      .select-wrap {
        position: relative;
        display: inline-flex;
      }

      .select-wrap::after {
        content: "";
        position: absolute;
        right: 13px;
        top: 50%;
        width: 7px;
        height: 7px;
        border-right: 1.6px solid var(--myhome-text-soft);
        border-bottom: 1.6px solid var(--myhome-text-soft);
        border-radius: 1px;
        transform: translateY(-70%) rotate(45deg);
        pointer-events: none;
      }

      select.field {
        appearance: none;
        padding-right: 36px;
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

      /*
       * Room under the fixed strips, so the last group is not permanently half-covered by
       * the pending bar. It is unconditional: a page whose height changed when a change
       * went pending would scroll under the reader on every drop.
       */
      .groups {
        margin-bottom: 96px;
      }

      /* The label that follows the pointer. Positioned by the drag, never by Lit. */
      .drag-ghost {
        position: fixed;
        left: 0;
        top: 0;
        z-index: 80;
        pointer-events: none;
        background: var(--myhome-card);
        color: var(--myhome-text);
        border: 1px solid var(--myhome-primary);
        border-radius: 8px;
        box-shadow: var(--myhome-shadow);
        padding: 10px 14px;
        font-size: 14px;
        max-width: 260px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    `]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._drag.stop(),this._trap.release()}updated(e){if(e.has("state")){let r=e.get("state");if(this._manageFocus(r),this._flip){let o=this._flip;this._flip=null,requestAnimationFrame(()=>mt(this.renderRoot,o))}}}_beforeMove(){this._flip=ut(this.renderRoot)}_manageFocus(e){let r=this.state.dialog!==null||this.state.review,o=(e?.dialog??null)!==null||(e?.review??!1);if(r&&!o){this._returnTo=this._activeElement(),requestAnimationFrame(()=>{let i=this.renderRoot.querySelector("[data-focus-root]");i&&this._trap.hold(i)});return}if(!r&&o){this._trap.release();let i=this._returnTo;this._returnTo=null,i?.isConnected&&requestAnimationFrame(()=>i.focus())}}_activeElement(){let e=this.renderRoot.activeElement;return e instanceof HTMLElement?e:null}get _overview(){return this.state.overview}get _locked(){return this._overview?.measuring!=null||this.state.applying}get _narrow(){return typeof matchMedia=="function"&&matchMedia("(max-width: 599px)").matches}_cover(e){return this._overview?.covers.find(r=>r.unique_id===e)}get _covers(){let e=this._overview;return e?nt(e,this.state.order):[]}get _rooms(){let e=new Set;for(let r of this._overview?.covers??[])r.area&&e.add(r.area);return Array.from(e).sort((r,o)=>r.localeCompare(o,this.i18n.language))}_matches(e){let r=this.state.search.trim().toLowerCase();return r&&!e.name.toLowerCase().includes(r)?!1:!this.state.room||e.area===this.state.room}_groupName(e){return e===null?this.i18n.t("panel.overview.group.no_profile"):this.i18n.t("panel.overview.group.profile",{profile:e})}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group.values_unknown"):this.i18n.t("panel.overview.group.values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),opening:this.i18n.number(e.values.opening_time,1),closing:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml")return this.i18n.t("panel.overview.group.from_file");if(!e.measured_on)return this.i18n.t("panel.overview.group.provenance_missing");let r=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.group.measured_on_gone",{date:r});let o=this.i18n.t("panel.overview.group.measured_on",{cover:e.measured_on_name,date:r}),i=(this._overview?.covers??[]).find(a=>a.unique_id===e.measured_on);if(i&&i.profile!==e.name){let a=i.profile??this.i18n.t("panel.overview.group.no_profile");o+=` · ${this.i18n.t("panel.profile.provenance_now_profile",{profile:a})}`}return o}get _groups(){let e=this._overview;if(!e)return[];let r=this._covers,o=a=>r.filter(p=>be(p,this.state.pending)===a&&this._matches(p)),i=e.profiles.map((a,p)=>({key:a.name,id:`group-${p}`,title:this.i18n.t("panel.overview.group.profile",{profile:a.name}),values:this._valuesLine(a),provenance:this._provenanceLine(a),warning:a.missing?this.i18n.t("panel.overview.group.missing"):"",covers:o(a.name)}));return i.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group.no_profile"),values:this.i18n.t("panel.overview.group.no_profile_note"),provenance:"",warning:"",covers:o(null)}),i}_endDrag(e){let r=this.state,o=r.drag,i=o?.insert??null,a=o?.over??null,p=o?this._cover(o.cover):void 0;if(this.actions.drag(null),!e||!p||a===null){o&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));return}let d=a==="none"?null:a,c=this._covers.map(v=>v.unique_id),u=ot(c,p.unique_id,i??{beforeId:null,afterId:null});this._beforeMove();let h=V(p.unique_id,r.pending),g=h?h.to:p.profile??null;if(d!==g){this.actions.setOrder(u),this.actions.assign(p,d);return}if(r.pending.length>0){this.actions.setOrder(u),this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));return}this.actions.reorder(u)}_renderControls(){return s`<div class="controls">
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
      <a class="cta secondary compact" href=${F} title=${this.i18n.t("panel.firstrun.note")}
        >${this.i18n.t("panel.firstrun.action.measure")}</a
      >
    </div>`}_renderFirstRun(){return s`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <a class="cta" href=${F}>${this.i18n.t("panel.firstrun.action.measure")}</a>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`}_renderStrips(){let e=this.state;if(e.drag)return Pt(this.i18n,e.drag.over==="none");if(e.armed){let r=this._cover(e.armed);return Et(this.i18n,r?.name??"",()=>this.actions.arm(null))}return e.applying?Tt(this.i18n):e.snack?At(this.i18n,e.snack.message,e.snack.undoToken?()=>this.actions.undo():null):e.pending.length>0&&!e.review?Ct({i18n:this.i18n,count:e.pending.length,locked:this._locked,lockedCover:this._overview?.measuring?.name??"",onDiscard:()=>{this._beforeMove(),this.actions.discardAll()},onReview:()=>this.actions.review(!0)}):l}_renderDialog(){let e=this.state.dialog?this._cover(this.state.dialog):void 0;return e?wt({i18n:this.i18n,cover:e,profiles:this._overview?.profiles??[],current:be(e,this.state.pending),onPick:r=>{this._beforeMove(),this.actions.assign(e,r)},onClose:()=>this.actions.dialog(null)}):l}_renderReview(){let e=this._overview;return!this.state.review||!e?l:Rt({i18n:this.i18n,pending:this.state.pending,covers:new Map(e.covers.map(r=>[r.unique_id,r])),profiles:new Map(e.profiles.map(r=>[r.name,r])),preview:this.state.preview,heights:this.state.heights,forced:this.state.heightsForced,showAll:this.state.showAll,applying:this.state.applying,refusal:this.state.writeError?this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{}):"",route:this._route,onHeight:(r,o)=>this.actions.height(r,o),onToggleShowAll:()=>this.actions.toggleShowAll(),onConfirm:()=>this.actions.confirm(),onClose:()=>this.actions.review(!1)})}render(){let e=this._overview;if(!e)return s`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return s`<div class="card notice">
        ${C(this.i18n.t("panel.overview.no_basic_covers"))}
      </div>`;if(e.profiles.length===0)return this._renderFirstRun();let r=this._groups,o=r.reduce((p,d)=>p+d.covers.length,0),i=this.state.search.trim()!==""||this.state.room!=="",a=this.state.drag;return s`
      <div class="intro">${this.i18n.md("panel.overview.explanation")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.summary",{profiles:e.profiles.length,covers:e.covers.length})}
      </p>
      ${this._renderControls()}
      ${o===0&&i?s`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${()=>this.actions.clearFilters()}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`:s`<div class="groups">
            ${r.map(p=>{let d=p.key??"none",c=a?.insert??null,u=c!==null&&c.group===d;return xt(p,{i18n:this.i18n,pending:this.state.pending,route:this._route,locked:this._locked,collapsed:this.state.armed!==null,over:a?.over===d,insertBefore:u?c.beforeId:null,insertEnd:u?c.end||c.afterId===p.covers.at(-1)?.unique_id:!1,dragging:a?.cover??null,onOpenProfile:h=>this.actions.openProfile(h),onOpenCover:h=>this.actions.openCover(h.unique_id),onGrab:this._onGrab,onRowPress:this._onRowPress,onPick:h=>this.actions.dialog(h),onWithdraw:h=>{this._beforeMove(),this.actions.withdraw(h)},onTarget:h=>{let g=this.state.armed?this._cover(this.state.armed):void 0;g&&(this._beforeMove(),this.actions.assign(g,h))}})})}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",re);var Mt={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},It=n=>(...t)=>({_$litDirective$:n,values:t}),ne=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,r){this._$Ct=t,this._$AM=e,this._$Ci=r}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var Lt="important",_r=" !"+Lt,Ot=It(class extends ne{constructor(n){if(super(n),n.type!==Mt.ATTRIBUTE||n.name!=="style"||n.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(n){return Object.keys(n).reduce((t,e)=>{let r=n[e];return r==null?t:t+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${r};`},"")}update(n,[t]){let{style:e}=n.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(t)),this.render(t);for(let r of this.ft)t[r]==null&&(this.ft.delete(r),r.includes("-")?e.removeProperty(r):e[r]=null);for(let r in t){let o=t[r];if(o!=null){this.ft.add(r);let i=typeof o=="string"&&o.endsWith(_r);r.includes("-")||i?e.setProperty(r,i?o.slice(0,-11):o,i?Lt:""):e[r]=o}}return w}});var zt=(n,t)=>n.summary?.note?s`<div class="stub">${n.summary.note}</div>`:l;var Ht=(n,t)=>{let e=n.options??[];return e.length===0?l:s`<div class="options" role="group" aria-label=${n.title}>
    ${e.map(r=>s`<button
        class="option"
        type="button"
        aria-pressed=${r.current?"true":"false"}
        @click=${()=>t.fire(r.action)}
      >
        <span class="option-head">
          <strong class="option-title">${r.title}</strong>
          ${r.chip?s`<span class="chip neutral">${r.chip}</span>`:l}
        </span>
        ${r.meta?s`<span class="option-meta">${r.meta}</span>`:l}
      </button>`)}
  </div>`};var Dt=(n,t)=>{let e=n.progress;if(!e)return s`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let r=Math.max(0,Math.min(1,e.fraction))*100;return s`<div class="progress-card">
    ${e.text?s`<p class="instruction">${e.text}</p>`:l}
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
      ${e.done?t.i18n.t("panel.screen.completed"):e.eta??""}
    </p>
  </div>`};var Nt=(n,t)=>{let e=n.press;if(!e)return s`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let r=e.state==="moving";return s`
    ${e.instruction?s`<p class="instruction">${e.instruction}</p>`:l}
    <div class="live">
      <div class="live-row">
        <span class="name">${t.i18n.t("panel.screen.motor")}</span>
        <span class="value ${r?"moving":""}">${e.motor??""}</span>
      </div>
      ${e.position?s`<div class="live-row">
            <span class="name">${t.i18n.t("panel.screen.position")}</span>
            <span class="value">${e.position}</span>
          </div>`:l}
    </div>
    ${e.note?s`<div
          class="note ${e.state==="problem"?"error":"success"}"
          role=${e.state==="problem"?"alert":"status"}
        >
          ${e.note}
        </div>`:l}
  `};var Ut=(n,t)=>{let e=n.options??[];if(e.length===0&&!n.field)return s`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let r=n.field;return s`
    <div class="options" role="group" aria-label=${n.title}>
      ${e.map(o=>s`<button
          class="option"
          type="button"
          aria-pressed=${o.current?"true":"false"}
          @click=${()=>t.fire(o.action)}
        >
          <strong class="option-title">${o.title}</strong>
          ${o.meta?s`<span class="option-meta">${o.meta}</span>`:l}
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
              @input=${o=>t.fire("field",o.target.value)}
            />
            ${r.unit?s`<span class="unit">${r.unit}</span>`:l}
          </div>
          ${r.error?s`<p class="error" id="gap-error" role="alert">${r.error}</p>`:l}
        </div>`:l}
  `};var qt=(n,t)=>{let e=n.field;return e?s`<div class="reading ${e.big===!1?"":"big"}">
    <label for="reading">${e.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${e.value}
        placeholder=${e.placeholder??""}
        aria-describedby=${e.error?"reading-error":e.hint?"reading-hint":l}
        aria-invalid=${e.error?"true":"false"}
        @input=${r=>t.fire("field",r.target.value)}
      />
      ${e.unit?s`<span class="unit">${e.unit}</span>`:l}
    </div>
    ${e.hint?s`<p class="hint" id="reading-hint">${e.hint}</p>`:l}
    ${e.error?s`<p class="error" id="reading-error" role="alert">${e.error}</p>`:l}
  </div>`:s`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`};var Ft=(n,t)=>{let e=n.summary;return e?s`
    <div class="summary">
      ${e.rows.map(r=>s`<div class="summary-row">
          <span class="label">${r.label}</span>
          ${r.before?s`<span class="before" aria-label=${t.i18n.t("panel.review.before")}
                >${r.before}</span
              >`:l}
          <span class="after" aria-label=${t.i18n.t("panel.review.after")}>${r.after}</span>
        </div>`)}
      ${e.note?s`<p class="note-line">${e.note}</p>`:l}
    </div>
    ${e.code?s`<pre class="code">${e.code}</pre>`:l}
  `:s`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`};var Bt=(n,t)=>n.summary?.rows?.length?s`<div class="summary">
    ${n.summary.rows.map(e=>s`<div class="summary-row">
        <span class="label">${e.label}</span>
        <span class="after">${e.after}</span>
      </div>`)}
    ${n.summary.note?s`<p class="note-line">${n.summary.note}</p>`:l}
  </div>`:l;var Wt=m`
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
`;var wr=/^\/myhome_static\/[A-Za-z0-9._~\-/]+$/,br=/(^|\/)\.\.?(\/|$)/,jt=/^[A-Za-z0-9 %.,\-]+$/,xr=n=>{if(!wr.test(n.src)||br.test(n.src))return null;let t=n.size&&jt.test(n.size)?n.size:"100% auto",e=n.pos&&jt.test(n.pos)?n.pos:"50% 60%";return{backgroundImage:`url("${n.src}")`,backgroundSize:t,backgroundPosition:e}},oe=class extends y{constructor(){super();this._fire=(e,r)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:e,value:r,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new x}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[A,M,I,J,Q,Wt,m`
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
          /*
           * "margin: 0 auto" centres the column, and in doing so it switches off the
           * cross-axis stretch a flex item would otherwise get - which left this element
           * as wide as its own text rather than as wide as the 1080 px the handoff fixes.
           * The explicit width says so.
           */
          width: 100%;
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
    `]}_renderOperative(e,r){switch(e.model){case"scelta":return Ht(e,r);case"pos":return Dt(e,r);case"click":return Nt(e,r);case"controllo":return Ut(e,r);case"metro":return qt(e,r);case"riepilogo":return Ft(e,r);case"esito":return Bt(e,r);case"lettura":return zt(e,r);default:return l}}_renderFooter(e,r){let o=e.secondary??[];return!e.primary&&o.length===0?l:s`<div class="footer">
      ${e.primary?s`<button
            class="big ${e.press?.state==="moving"?"moving":""}"
            type="button"
            ?disabled=${e.primary.disabled}
            @click=${()=>this._fire(e.primary.action)}
          >
            ${e.primary.label}
          </button>`:l}
      ${o.map(i=>s`<button
          class="cta ${i.kind==="text"?"text":"secondary"}"
          type="button"
          ?disabled=${i.disabled}
          @click=${()=>r.fire(i.action)}
        >
          ${i.label}
        </button>`)}
    </div>`}render(){let e=this.model;if(!e)return l;let r={i18n:this.i18n,fire:this._fire},o=e.model==="pos",i=e.image?xr(e.image):null;return s`<div class="screen">
      <main class=${o?"single":""}>
        <div class="text-column">
          ${e.phase?s`<p class="phase">
                ${this.i18n.t("panel.screen.phase",{phase:e.phase.label,index:e.phase.index,count:e.phase.count})}
              </p>`:l}
          ${e.newText?s`<p class="new-text">${this.i18n.t("panel.screen.new_text")}</p>`:l}
          <h1 class="screen-title">
            ${e.outcome?s`<span class="outcome-icon ${e.outcome}" aria-hidden="true"></span>`:l}
            <span>${e.title}</span>
          </h1>
          ${i?s`<div
                class="drawing"
                role="img"
                aria-label=${e.image?.alt??""}
                style=${Ot(i)}
              ></div>`:l}
          ${e.body?s`<div class="prose">${C(e.body)}</div>`:l}
        </div>
        <div class="right">
          ${this._renderOperative(e,r)} ${this._renderFooter(e,r)}
        </div>
      </main>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",oe);var $r=3e4,kr=7e3,Rr=400,Pe=class extends y{constructor(){super();this._i18n=new x;this._router=new Y;this._store=new Z(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._snackTimer=null;this._previewTimer=null;this._previewSeq=0;this._onReturn=()=>{!this._started||document.hidden||this._refresh()};this._assignActions={search:e=>this._store.set({search:e}),room:e=>this._store.set({room:e}),clearFilters:()=>this._store.set({search:"",room:""}),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:(e,r)=>{if(this._locked)return;let{pending:o,withdrawn:i}=rt(this._store.state.pending,e,r);this._store.set({pending:o,dialog:null,armed:null,writeError:null}),this._store.announce(i?this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name}):this._i18n.t("panel.assign.announce.pending",{cover:e.name,target:r===null?this._i18n.t("panel.assign.target_none"):this._i18n.t("panel.assign.target_profile",{profile:r})})),this._schedulePreview()},withdraw:e=>{this._store.set({pending:this._store.state.pending.filter(r=>r.cover!==e.unique_id)}),this._store.announce(this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name})),this._schedulePreview()},discardAll:()=>{this._store.set({...Se}),this._store.announce(this._i18n.t("panel.assign.announce.discarded"))},reorder:e=>{this._locked||!this._store.state.entryId||(this._store.set({order:e}),this._write(()=>Je(this.hass.connection,this._store.state.entryId,e),r=>{this._store.set({order:null}),this._store.setOverview(r.overview),this._snack(this._i18n.t("panel.toast.order_saved"),r.undo_token),this._store.announce(this._i18n.t("panel.assign.announce.reordered"))}))},setOrder:e=>this._store.set({order:e}),drag:e=>this._store.set({drag:e?{cover:e.unique_id,name:e.name,over:null,insert:null}:null}),over:e=>{let r=this._store.state.drag;r&&this._store.set({drag:{...r,over:e?.group??null,insert:e?{...e}:null}})},arm:e=>{this._store.set({armed:e?e.unique_id:null}),e&&this._store.announce(this._i18n.t("panel.assign.announce.armed"))},dialog:e=>this._store.set({dialog:e?e.unique_id:null}),review:e=>{this._store.set({review:e,writeError:null,heightsForced:!1}),e&&this._refreshPreview()},height:(e,r)=>{this._store.set({heights:{...this._store.state.heights,[e]:r}}),this._schedulePreview()},toggleShowAll:()=>this._store.set({showAll:!this._store.state.showAll}),confirm:()=>{this._confirm()},undo:()=>{this._undo()},announce:e=>this._store.announce(e)};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[A,M,I,Q,ct,m`
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

      /* The page's one <h1>, styled as the toolbar's title and not as a heading. */
      .toolbar .title {
        flex: 1;
        min-width: 0;
        margin: 0;
        font-size: inherit;
        font-weight: inherit;
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

      /* Waiting is not a refusal, and must not borrow the error colour to say so. */
      .card.waiting {
        color: var(--myhome-text-soft);
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
    `]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(e=>this._store.set({route:e})),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._stopPolling(),this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._previewTimer&&(clearTimeout(this._previewTimer),this._previewTimer=null);let e=this._unsubscribeWs;this._unsubscribeWs=null,e?.().catch(()=>{})}shouldUpdate(e){return e.size>1||!e.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(e){if(e.has("route")&&(this._router.setHostPath(this.route?.path),this._store.set({route:this._router.current})),!(!e.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_languageOf(e){return e?.locale?.language||e?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,await this._loadTexts(),await this._refresh(),await this._listen())}async _loadTexts(){let e=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,e)}catch{}this._language=e,this.requestUpdate()}async _refresh(){try{let e=await Ke(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(e)}catch(e){this._store.setError(T(e))}}async _listen(){try{this._unsubscribeWs=await Ye(this.hass.connection,this._store.state.entryId,e=>this._onEvent(e)),this._store.set({connection:"live"}),this._stopPolling()}catch(e){_e(e)||console.warn("MyHOME panel: live updates are not available",T(e)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(e){if(e.type==="overview"){this._store.setOverview(e.overview),this._store.state.review&&this._schedulePreview();return}if(e.type==="measuring"){let r=this._store.state.overview;if(!r)return;this._store.set({overview:{...r,measuring:e.cover_unique_id?{cover_unique_id:e.cover_unique_id,name:e.name??""}:null}}),e.cover_unique_id&&(this._store.set({armed:null,drag:null}),this._store.announce(this._i18n.t("panel.banner.measuring.body",{cover:e.name??""})))}}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},$r))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}get _version(){return this.panel?.config?.version??""}_navigate(e){this._router.navigate(e)}_renderMenuButton(){return this.narrow?et("ha-menu-button")?s`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:s`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>tt(this)}
    >
      ☰
    </button>`:l}_renderBackButton(){return this._store.state.route.view==="overview"?l:s`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.back")}
      @click=${()=>this._navigate("/")}
    >
      ←
    </button>`}_renderPlaceholder(e,r){let o={id:"panel.common.not_yet",model:"lettura",title:e,body:r,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return s`<myhome-screen
      .model=${o}
      .i18n=${this._i18n}
      @myhome-screen-action=${i=>{i.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}get _locked(){let e=this._store.state;return e.overview?.measuring!=null||e.applying}async _confirm(){let e=this._store.state,r=e.entryId;if(this._locked||!r||e.pending.length===0)return;if(e.pending.filter(d=>{let c=e.overview?.covers.find(u=>u.unique_id===d.cover);return c!==void 0&&st(c,d)&&q(e.heights[d.cover])!==null}).length>0){this._store.set({heightsForced:!0}),this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));return}let i=xe(e.pending,e.heights),a=e.order??void 0,p=i.length;this._store.announce(this._i18n.t("panel.assign.announce.applying")),await this._write(()=>Ze(this.hass.connection,r,i,a),d=>{this._store.set({...Se}),this._store.setOverview(d.overview),this._snack(p===1?this._i18n.t("panel.toast.assigned_one"):this._i18n.t("panel.toast.assigned",{count:p}),d.undo_token)})}async _undo(){let e=this._store.state,r=e.snack?.undoToken;if(!r||!e.entryId)return;let o=e.entryId;this._clearSnack(),await this._write(()=>Qe(this.hass.connection,o,r),i=>{this._store.setOverview(i.overview),this._snack(this._i18n.t("panel.toast.undone"),null)})}async _write(e,r){this._store.set({applying:!0,writeError:null});try{let o=await e();this._store.set({applying:!1}),r(o)}catch(o){let i=T(o);this._store.set({applying:!1,writeError:i}),this._store.announce(this._i18n.refusal(i.translation_key,i.translation_placeholders??{}))}}_snack(e,r){this._clearSnack(),this._store.set({snack:{message:e,undoToken:r}}),this._store.announce(e),this._snackTimer=setTimeout(()=>{this._snackTimer=null,this._store.set({snack:null})},kr)}_clearSnack(){this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._store.set({snack:null})}_schedulePreview(){this._store.state.review&&(this._previewTimer&&clearTimeout(this._previewTimer),this._previewTimer=setTimeout(()=>{this._previewTimer=null,this._refreshPreview()},Rr))}async _refreshPreview(){let e=this._store.state;if(!e.entryId||e.pending.length===0){this._store.set({preview:null});return}let r=++this._previewSeq;this._store.set({previewing:!0});try{let o=await Xe(this.hass.connection,e.entryId,xe(e.pending,e.heights));r===this._previewSeq&&this._store.set({preview:o.items,previewing:!1})}catch(o){r===this._previewSeq&&this._store.set({previewing:!1}),_e(o)||console.warn("MyHOME panel: the preview could not be read",T(o))}}_renderView(){let e=this._store.state;if(e.status==="loading")return s`<div class="card waiting" role="status">
        ${this._i18n.t("panel.common.loading")}
      </div>`;if(e.status==="error"||!e.overview){let o=e.error;return s`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(o?.translation_key,o?.translation_placeholders??{})}
        </div>
        <div class="soft">${o?`${o.code}: ${o.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._refresh()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${F}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?s` · ${this._version}`:l}
        </div>
      </div>`}let r=e.route;if(r.view==="cover"){let o=e.overview.covers.find(i=>i.unique_id===r.params.id);return this._renderPlaceholder(o?this._i18n.t("panel.detail.named",{cover:o.name}):this._i18n.t("panel.detail.unknown"),this._i18n.t("panel.common.not_yet"))}if(r.view==="profile"){let o=r.params.name,i=e.overview.profiles.some(a=>a.name===o);return this._renderPlaceholder(i?this._i18n.t("panel.profile.name",{profile:o}):this._i18n.t("panel.profile.unknown"),this._i18n.t("panel.common.not_yet"))}return r.view!=="overview"?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):s`<myhome-overview
      .i18n=${this._i18n}
      .state=${e}
      .actions=${this._assignActions}
    ></myhome-overview>`}render(){let e=this._store.state,r=this._i18n.t("panel.overview.title"),o=e.overview?.entries.find(a=>a.entry_id===e.entryId),i=e.overview?.measuring??null;return s`
      <div class="toolbar">
        ${this._renderMenuButton()} ${this._renderBackButton()}
        <h1 class="title">${r}</h1>
        ${o&&(e.overview?.entries.length??0)>1?s`<div class="gateway">
              ${this._i18n.t("panel.common.gateway",{gateway:o.title})}
            </div>`:l}
      </div>
      ${i?ht(this._i18n,i.name,F):l}
      <div class="content">
        ${dt(e.announce)} ${this._renderView()}
        ${e.connection==="polling"&&e.status==="ready"?s`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:l}
      </div>
    `}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",Pe);export{Pe as MyHomeCalibrationPanel};
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
