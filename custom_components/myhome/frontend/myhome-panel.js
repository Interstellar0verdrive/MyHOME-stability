/* MyHOME calibration panel */
var ve=globalThis,ge=ve.ShadowRoot&&(ve.ShadyCSS===void 0||ve.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,je=Symbol(),_t=new WeakMap,ee=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==je)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(ge&&t===void 0){let i=e!==void 0&&e.length===1;i&&(t=_t.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&_t.set(e,t))}return t}toString(){return this.cssText}},wt=n=>new ee(typeof n=="string"?n:n+"",void 0,je),m=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((i,r,o)=>i+(s=>{if(s._$cssResult$===!0)return s.cssText;if(typeof s=="number")return s;throw Error("Value passed to 'css' function must be a 'css' function result: "+s+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+n[o+1],n[0]);return new ee(e,n,je)},bt=(n,t)=>{if(ge)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let i=document.createElement("style"),r=ve.litNonce;r!==void 0&&i.setAttribute("nonce",r),i.textContent=e.cssText,n.appendChild(i)}},Ve=ge?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let i of t.cssRules)e+=i.cssText;return wt(e)})(n):n;var{is:Vi,defineProperty:Yi,getOwnPropertyDescriptor:Xi,getOwnPropertyNames:Zi,getOwnPropertySymbols:Qi,getPrototypeOf:Ji}=Object,fe=globalThis,yt=fe.trustedTypes,en=yt?yt.emptyScript:"",tn=fe.reactiveElementPolyfillSupport,te=(n,t)=>n,Ye={toAttribute(n,t){switch(t){case Boolean:n=n?en:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},$t=(n,t)=>!Vi(n,t),xt={attribute:!0,type:String,converter:Ye,reflect:!1,useDefault:!1,hasChanged:$t};Symbol.metadata??=Symbol("metadata"),fe.litPropertyMetadata??=new WeakMap;var T=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=xt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let i=Symbol(),r=this.getPropertyDescriptor(t,i,e);r!==void 0&&Yi(this.prototype,t,r)}}static getPropertyDescriptor(t,e,i){let{get:r,set:o}=Xi(this.prototype,t)??{get(){return this[e]},set(s){this[e]=s}};return{get:r,set(s){let p=r?.call(this);o?.call(this,s),this.requestUpdate(t,p,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??xt}static _$Ei(){if(this.hasOwnProperty(te("elementProperties")))return;let t=Ji(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(te("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(te("properties"))){let e=this.properties,i=[...Zi(e),...Qi(e)];for(let r of i)this.createProperty(r,e[r])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[i,r]of e)this.elementProperties.set(i,r)}this._$Eh=new Map;for(let[e,i]of this.elementProperties){let r=this._$Eu(e,i);r!==void 0&&this._$Eh.set(r,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let i=new Set(t.flat(1/0).reverse());for(let r of i)e.unshift(Ve(r))}else t!==void 0&&e.push(Ve(t));return e}static _$Eu(t,e){let i=e.attribute;return i===!1?void 0:typeof i=="string"?i:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return bt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){let i=this.constructor.elementProperties.get(t),r=this.constructor._$Eu(t,i);if(r!==void 0&&i.reflect===!0){let o=(i.converter?.toAttribute!==void 0?i.converter:Ye).toAttribute(e,i.type);this._$Em=t,o==null?this.removeAttribute(r):this.setAttribute(r,o),this._$Em=null}}_$AK(t,e){let i=this.constructor,r=i._$Eh.get(t);if(r!==void 0&&this._$Em!==r){let o=i.getPropertyOptions(r),s=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:Ye;this._$Em=r;let p=s.fromAttribute(e,o.type);this[r]=p??this._$Ej?.get(r)??p,this._$Em=null}}requestUpdate(t,e,i,r=!1,o){if(t!==void 0){let s=this.constructor;if(r===!1&&(o=this[t]),i??=s.getPropertyOptions(t),!((i.hasChanged??$t)(o,e)||i.useDefault&&i.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(s._$Eu(t,i))))return;this.C(t,e,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:r,wrapped:o},s){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,s??e??this[t]),o!==!0||s!==void 0)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),r===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[r,o]of this._$Ep)this[r]=o;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[r,o]of i){let{wrapped:s}=o,p=this[r];s!==!0||this._$AL.has(r)||p===void 0||this.C(r,void 0,o,p)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(e)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};T.elementStyles=[],T.shadowRootOptions={mode:"open"},T[te("elementProperties")]=new Map,T[te("finalized")]=new Map,tn?.({ReactiveElement:T}),(fe.reactiveElementVersions??=[]).push("2.1.2");var it=globalThis,kt=n=>n,_e=it.trustedTypes,St=_e?_e.createPolicy("lit-html",{createHTML:n=>n}):void 0,At="$lit$",D=`lit$${Math.random().toFixed(9).slice(2)}$`,It="?"+D,nn=`<${It}>`,U=document,ne=()=>U.createComment(""),re=n=>n===null||typeof n!="object"&&typeof n!="function",nt=Array.isArray,rn=n=>nt(n)||typeof n?.[Symbol.iterator]=="function",Xe=`[ 	
\f\r]`,ie=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Rt=/-->/g,Et=/>/g,N=RegExp(`>|${Xe}(?:([^\\s"'>=/]+)(${Xe}*=${Xe}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Pt=/'/g,Tt=/"/g,Mt=/^(?:script|style|textarea|title)$/i,rt=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),a=rt(1),Dn=rt(2),zn=rt(3),C=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Ct=new WeakMap,q=U.createTreeWalker(U,129);function Lt(n,t){if(!nt(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return St!==void 0?St.createHTML(t):t}var on=(n,t)=>{let e=n.length-1,i=[],r,o=t===2?"<svg>":t===3?"<math>":"",s=ie;for(let p=0;p<e;p++){let d=n[p],c,u,h=-1,g=0;for(;g<d.length&&(s.lastIndex=g,u=s.exec(d),u!==null);)g=s.lastIndex,s===ie?u[1]==="!--"?s=Rt:u[1]!==void 0?s=Et:u[2]!==void 0?(Mt.test(u[2])&&(r=RegExp("</"+u[2],"g")),s=N):u[3]!==void 0&&(s=N):s===N?u[0]===">"?(s=r??ie,h=-1):u[1]===void 0?h=-2:(h=s.lastIndex-u[2].length,c=u[1],s=u[3]===void 0?N:u[3]==='"'?Tt:Pt):s===Tt||s===Pt?s=N:s===Rt||s===Et?s=ie:(s=N,r=void 0);let _=s===N&&n[p+1].startsWith("/>")?" ":"";o+=s===ie?d+nn:h>=0?(i.push(c),d.slice(0,h)+At+d.slice(h)+D+_):d+D+(h===-2?p:_)}return[Lt(n,o+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),i]},oe=class n{constructor({strings:t,_$litType$:e},i){let r;this.parts=[];let o=0,s=0,p=t.length-1,d=this.parts,[c,u]=on(t,e);if(this.el=n.createElement(c,i),q.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(r=q.nextNode())!==null&&d.length<p;){if(r.nodeType===1){if(r.hasAttributes())for(let h of r.getAttributeNames())if(h.endsWith(At)){let g=u[s++],_=r.getAttribute(h).split(D),F=/([.?@])?(.*)/.exec(g);d.push({type:1,index:o,name:F[2],strings:_,ctor:F[1]==="."?Qe:F[1]==="?"?Je:F[1]==="@"?et:V}),r.removeAttribute(h)}else h.startsWith(D)&&(d.push({type:6,index:o}),r.removeAttribute(h));if(Mt.test(r.tagName)){let h=r.textContent.split(D),g=h.length-1;if(g>0){r.textContent=_e?_e.emptyScript:"";for(let _=0;_<g;_++)r.append(h[_],ne()),q.nextNode(),d.push({type:2,index:++o});r.append(h[g],ne())}}}else if(r.nodeType===8)if(r.data===It)d.push({type:2,index:o});else{let h=-1;for(;(h=r.data.indexOf(D,h+1))!==-1;)d.push({type:7,index:o}),h+=D.length-1}o++}}static createElement(t,e){let i=U.createElement("template");return i.innerHTML=t,i}};function j(n,t,e=n,i){if(t===C)return t;let r=i!==void 0?e._$Co?.[i]:e._$Cl,o=re(t)?void 0:t._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),o===void 0?r=void 0:(r=new o(n),r._$AT(n,e,i)),i!==void 0?(e._$Co??=[])[i]=r:e._$Cl=r),r!==void 0&&(t=j(n,r._$AS(n,t.values),r,i)),t}var Ze=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:i}=this._$AD,r=(t?.creationScope??U).importNode(e,!0);q.currentNode=r;let o=q.nextNode(),s=0,p=0,d=i[0];for(;d!==void 0;){if(s===d.index){let c;d.type===2?c=new se(o,o.nextSibling,this,t):d.type===1?c=new d.ctor(o,d.name,d.strings,this,t):d.type===6&&(c=new tt(o,this,t)),this._$AV.push(c),d=i[++p]}s!==d?.index&&(o=q.nextNode(),s++)}return q.currentNode=U,r}p(t){let e=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}},se=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,r){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=j(this,t,e),re(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==C&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):rn(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&re(this._$AH)?this._$AA.nextSibling.data=t:this.T(U.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:i}=t,r=typeof i=="number"?this._$AC(t):(i.el===void 0&&(i.el=oe.createElement(Lt(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===r)this._$AH.p(e);else{let o=new Ze(r,this),s=o.u(this.options);o.p(e),this.T(s),this._$AH=o}}_$AC(t){let e=Ct.get(t.strings);return e===void 0&&Ct.set(t.strings,e=new oe(t)),e}k(t){nt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,i,r=0;for(let o of t)r===e.length?e.push(i=new n(this.O(ne()),this.O(ne()),this,this.options)):i=e[r],i._$AI(o),r++;r<e.length&&(this._$AR(i&&i._$AB.nextSibling,r),e.length=r)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let i=kt(t).nextSibling;kt(t).remove(),t=i}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},V=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,r,o){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=r,this.options=o,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=l}_$AI(t,e=this,i,r){let o=this.strings,s=!1;if(o===void 0)t=j(this,t,e,0),s=!re(t)||t!==this._$AH&&t!==C,s&&(this._$AH=t);else{let p=t,d,c;for(t=o[0],d=0;d<o.length-1;d++)c=j(this,p[i+d],e,d),c===C&&(c=this._$AH[d]),s||=!re(c)||c!==this._$AH[d],c===l?t=l:t!==l&&(t+=(c??"")+o[d+1]),this._$AH[d]=c}s&&!r&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Qe=class extends V{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},Je=class extends V{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},et=class extends V{constructor(t,e,i,r,o){super(t,e,i,r,o),this.type=5}_$AI(t,e=this){if((t=j(this,t,e,0)??l)===C)return;let i=this._$AH,r=t===l&&i!==l||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,o=t!==l&&(i===l||r);r&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},tt=class{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){j(this,t)}};var sn=it.litHtmlPolyfillSupport;sn?.(oe,se),(it.litHtmlVersions??=[]).push("3.3.3");var Ot=(n,t,e)=>{let i=e?.renderBefore??t,r=i._$litPart$;if(r===void 0){let o=e?.renderBefore??null;i._$litPart$=r=new se(t.insertBefore(ne(),o),o,void 0,e??{})}return r._$AI(n),r};var ot=globalThis,f=class extends T{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Ot(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return C}};f._$litElement$=!0,f.finalized=!0,ot.litElementHydrateSupport?.({LitElement:f});var an=ot.litElementPolyfillSupport;an?.({LitElement:f});(ot.litElementVersions??=[]).push("4.2.2");var Dt={"panel.assign.action.discard_all":"Discard everything","panel.assign.action.review":"Review and confirm","panel.assign.action.review_hint":"Review and confirm the assignments","panel.assign.action.withdraw":"Withdraw this change","panel.assign.announce.applying":"The changes are being applied.","panel.assign.announce.armed":"Tap the destination group.","panel.assign.announce.discarded":"Every pending change has been discarded.","panel.assign.announce.drag_cancelled":"Drag cancelled.","panel.assign.announce.missing_travel":"Some covers have no travel.","panel.assign.announce.pending":"«{cover}» is pending, towards {target}. Nothing is written yet.","panel.assign.announce.reordered":"Order updated: it will be remembered.","panel.assign.announce.withdrawn":"«{cover}» goes back where it was: the change is withdrawn.","panel.assign.armed":"Tap the destination group for «{cover}»","panel.assign.drop_zone":"Take out of the profile — drop here","panel.assign.handle":"Move {cover} to another group, or reorder it","panel.assign.handle_hint":"Drag to assign or reorder, Enter to pick from a list","panel.assign.pending.all_own":"All values its own: nothing changes","panel.assign.pending.count":"{count} pending changes — nothing is written yet","panel.assign.pending.count_one":"1 pending change — nothing is written yet","panel.assign.pending.route":"{from} → {to}","panel.assign.pending.route_name":"«{profile}»","panel.assign.pending.some_own":"Own values: those stay","panel.assign.target_none":"«No profile»","panel.assign.target_profile":"the profile «{profile}»","panel.banner.applying.body":"The covers are unavailable for a few seconds","panel.banner.applying.title":"The changes are being applied…","panel.banner.measuring.action.resume":"Resume the session","panel.banner.measuring.action.stop":"End it","panel.banner.measuring.body":"A guided calibration is using «{cover}». Until the session ends, this panel only reads: nothing is written.","panel.banner.measuring.title":"Measurement in progress","panel.common.action.back":"Back","panel.common.action.cancel":"Cancel","panel.common.action.close":"Close","panel.common.action.configure":"Open Configure","panel.common.action.hide_all":"Hide the roll coefficients","panel.common.action.menu":"Open the Home Assistant menu","panel.common.action.retry":"Try again","panel.common.action.save":"Save","panel.common.action.show_all":"Show every value, roll coefficients included","panel.common.advanced.body":"Slat opening time and roll coefficients are parameters of the position model and should only be changed with a precise understanding of what they mean and how they affect the position. When in doubt, obtaining them from the guided calibration is strongly recommended: it measures them on the real cover.","panel.common.advanced.title":"Advanced parameters","panel.common.all_rooms":"All rooms","panel.common.gateway":"Gateway {gateway}","panel.common.loading":"Loading…","panel.common.not_yet":"This screen arrives in a later version. Until then «Configure» does everything it will do.","panel.common.opens_configure":"This opens the Configure dialog. The panel refreshes on its own when it closes.","panel.common.polling":"Live updates are not available on this version: the page refreshes on its own every 30 seconds.","panel.common.reconnected":"Home Assistant is answering again: this page has just been read afresh.","panel.common.required":"This field cannot be left empty.","panel.common.room_filter":"Filter by room","panel.common.search":"Search for a cover","panel.common.unit.centimetres":"cm","panel.common.unit.seconds":"s","panel.detail.action.assign":"Assign to a profile…","panel.detail.action.correct":"Correct…","panel.detail.action.correct_note":"If it stops in the wrong place: times only, times and rolls, or the thorough calibration only","panel.detail.action.edit":"Edit the values by hand","panel.detail.action.measure_again":"Measure again","panel.detail.action.measure_again_note":"Full basic calibration, in the dialog","panel.detail.action.remove":"Remove the measurement…","panel.detail.action.thorough":"Thorough calibration","panel.detail.action.thorough_note":"On top: readings at 25 and 75 % per direction, and a check","panel.detail.action.travel":"Set the curtain travel…","panel.detail.correct.intro":"The correction opens the Configure dialog on the path chosen. When it comes back, the panel refreshes on its own.","panel.detail.correct.thorough":"Thorough calibration only","panel.detail.correct.thorough_note":"Readings at 25 and 75 % per direction, and a check","panel.detail.correct.times":"Times only","panel.detail.correct.times_note":"One run per direction, the rolls stay","panel.detail.correct.times_rolls":"Times and rolls","panel.detail.correct.times_rolls_note":"Full basic calibration","panel.detail.destination.defaults":"the default values","panel.detail.destination.file":"the values of the configuration file","panel.detail.destination.profile":"the values inherited from the profile «{profile}»","panel.detail.edit.action.save":"Save the values","panel.detail.edit.empty":"empty = nothing to say","panel.detail.edit.inherits":"inherits {value}","panel.detail.edit.intro":"These values count for this cover alone and beat both the profile and the file. A field left empty is not a zero: it means «nothing to say about this one», and the value goes back to coming from the profile or from the file. Emptying every field is the same as removing the measurement.","panel.detail.edit.title":"Edit the values by hand","panel.detail.level_basic":"basic calibration","panel.detail.level_thorough":"thorough calibration","panel.detail.measured_at":"Measured on {date}","panel.detail.remove.action":"Remove the measurement","panel.detail.remove.body":"The measurements made on «{cover}» will be removed and cannot be recovered. The cover will go back to using {destination}.","panel.detail.remove.title":"Remove the measurement?","panel.detail.remove.travel_stays":"The curtain travel stays: somebody measured it with a tape.","panel.detail.source.default":"default value","panel.detail.source.file":"from the configuration file","panel.detail.source.own":"own value, measured on this cover","panel.detail.source.profile":"inherited from the profile «{profile}»","panel.detail.title":"Cover detail","panel.detail.unknown":"This gateway has no cover with that identifier.","panel.detail.values.intro":"What the cover is using right now, value by value, with where it comes from: a value of its own always wins; then the assigned profile, then the file, then the defaults.","panel.detail.values.title":"Values in use","panel.detail.verify_note":"{deviation} cm out at the check","panel.dialog.option.current":"current","panel.dialog.option.none":"No profile","panel.dialog.option.none_meta":"Values from the configuration file, or the defaults. The travel and the values of its own stay.","panel.dialog.option.profile":"Profile «{profile}»","panel.dialog.option.profile_meta":"{travel} cm · ascent {opening} s · descent {closing} s","panel.dialog.subtitle":"«{cover}» — the choice stays pending until it is confirmed.","panel.dialog.title":"Which profile?","panel.error.no_connection":"Home Assistant is not answering. The panel will try again.","panel.error.not_found":"The panel could not read this gateway.","panel.firstrun.action.measure":"Measure a cover","panel.firstrun.body":"A **profile** describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.firstrun.how":"A profile is not written, it is measured. Pick one representative cover and measure it once, with the guided calibration: about three minutes. Similar covers can then follow it.","panel.firstrun.note":"This opens the Configure dialog: that is where the measuring happens. When it is done, the profile appears here.","panel.firstrun.title":"No profile yet","panel.overview.action.clear_filters":"Clear the search and the filter","panel.overview.cover.follows":"follows «{profile}»","panel.overview.cover.origin_adjusted":"Adjusted","panel.overview.cover.origin_inherited":"Inherited","panel.overview.cover.profile_missing":"The profile «{profile}» is no longer defined: this cover is running on its own configuration.","panel.overview.cover.travel":"travel {travel} cm","panel.overview.cover.travel_needed":"travel to be entered","panel.overview.cover.travel_unknown":"travel not recorded","panel.overview.explanation":"A **profile** describes a type of cover: how long it takes to run, how long the slats take and how the curtain winds onto the roll. Each cover may follow one, and Home Assistant adapts it to that cover's own travel.","panel.overview.group.count":"{count} covers","panel.overview.group.count_one":"1 cover","panel.overview.group.empty":"No cover in this group.","panel.overview.group.from_file":"Stated in the configuration file: this is changed there, not here.","panel.overview.group.measured_on":"Measured on {cover} · {date}","panel.overview.group.measured_on_gone":"Measured on a cover this gateway no longer has · {date}","panel.overview.group.missing":"This profile is not defined any more: the covers below have quietly fallen back to their own configuration.","panel.overview.group.no_profile":"No profile","panel.overview.group.no_profile_note":"Values from the configuration file, or the defaults. It is not a fault: a cover with measurements of its own sits perfectly well here.","panel.overview.group.open":"Open the profile card","panel.overview.group.profile":"Profile «{profile}»","panel.overview.group.provenance_missing":"Where it was measured is not recorded.","panel.overview.group.values":"Reference travel {travel} cm · ascent {opening} s · descent {closing} s · slats {slat} s","panel.overview.group.values_unknown":"Nobody defines this profile, so it has no values.","panel.overview.no_basic_covers":"Every cover of this gateway reports its own position, so there is no travel model to calibrate and nothing for this panel to do.","panel.overview.no_basic_covers_title":"Nothing to calibrate on this gateway","panel.overview.no_results":"No cover matches this search.","panel.overview.summary":"Profiles: {profiles} · Basic covers: {covers}","panel.overview.title":"Profiles and covers","panel.profile.action.delete":"Delete the profile…","panel.profile.action.edit":"Edit the values…","panel.profile.action.rename":"Rename…","panel.profile.delete.action":"Delete the profile","panel.profile.delete.affects":"It affects these covers:","panel.profile.delete.body":"They will go back to the values of the configuration file, where those exist, or to the defaults. Their travels and their own values stay. The profile's measurements cannot be recovered.","panel.profile.delete.title":"Delete the profile «{profile}»?","panel.profile.edit.action.save":"Apply to {count} covers","panel.profile.edit.action.save_one":"Apply to 1 cover","panel.profile.edit.intro":"A change to the profile changes everything for the covers that inherit its values, and only the inherited values for the adjusted ones: the values of their own stay, key by key.","panel.profile.edit.reach":"The change reaches {target}","panel.profile.edit.reach_all":"every one of the {count} covers that follow the profile","panel.profile.edit.reach_one":"1 cover","panel.profile.edit.title":"Edit the values","panel.profile.followers.adjusted":"adjusted: own values for {keys}","panel.profile.followers.count":"{count} covers follow it","panel.profile.followers.count_one":"1 cover follows it","panel.profile.followers.inherited":"inherited","panel.profile.followers.measured":"measured: nothing inherited","panel.profile.followers.none":"No cover follows it.","panel.profile.from_file":"Profile of the configuration file: read-only here.","panel.profile.impact.invalid":"correct the fields to see the preview","panel.profile.impact.kept":"own values stay: {keys}","panel.profile.impact.no_change":"no change: all values are its own","panel.profile.impact.no_travel":"travel not recorded: it will use the profile's values as they are","panel.profile.impact.state_adjusted":"adjusted: only the inherited values change","panel.profile.impact.state_inherited":"inherited: everything changes","panel.profile.impact.state_measured":"measured","panel.profile.impact.title":"Impact preview","panel.profile.name":"Profile «{profile}»","panel.profile.provenance":"Measured on {cover} · {date}","panel.profile.provenance_missing":"Where it was measured is not recorded.","panel.profile.provenance_now_none":"now follows no profile","panel.profile.provenance_now_profile":"now follows «{profile}»","panel.profile.reference_travel":"Reference travel","panel.profile.rename.action":"Rename","panel.profile.rename.field":"New name of the profile","panel.profile.rename.rule":"Letters, digits and underscores only, no more than 64 of them: no spaces, no accents — the name is also a key of the configuration file. The rename follows every cover that uses the profile.","panel.profile.rename.title":"Rename the profile","panel.profile.stored":"Stored profile","panel.profile.title":"Profile card","panel.profile.unknown":"No profile of that name is defined or followed here.","panel.profile.values":"Values of the profile","panel.review.action.back":"Back to the overview","panel.review.action.confirm":"Confirm {count} assignments","panel.review.action.confirm_one":"Confirm 1 assignment","panel.review.action.missing_travel":"{count} travels missing","panel.review.action.missing_travel_one":"1 travel missing","panel.review.after":"After","panel.review.before":"Before","panel.review.intro":"The changes are written all at once. For each cover, this is what it will really use: the profile's values brought to its own travel.","panel.review.note.all_own":"It has values of its own for everything: nothing changes. The profile would only count for values removed later on.","panel.review.note.back_to_defaults":"The default values come back: the position in per cent will be a rough estimate. The travel and any value of its own stay.","panel.review.note.back_to_file":"The values of the configuration file come back. The travel and any value of its own stay.","panel.review.note.scaled":"Values of the profile «{profile}» (measured on {reference} cm) brought to a travel of {travel} cm.","panel.review.note.some_own":"It has some values of its own: those stay. Only the inherited values change.","panel.review.title":"Review and confirm","panel.review.travel.aria":"Curtain travel in centimetres","panel.review.travel.hint":"A profile is the measurement of one cover with a certain travel, and it is brought to the others in proportion. The travel of these is not known: measure the distance the bottom edge covers from fully closed to fully open, and write it in centimetres (decimals with a comma or with a point).","panel.review.travel.label":"Curtain travel","panel.review.travel.placeholder":"e.g. 145","panel.review.travel.required":"The travel is needed, in centimetres.","panel.review.travel.title":"How far does the curtain of these covers run?","panel.screen.completed":"Completed","panel.screen.motor":"Motor","panel.screen.new_text":"new text — not translated yet","panel.screen.not_in_this_version":"This step belongs to the guided calibration, which moves into the panel in a later version.","panel.screen.phase":"{phase} · {index} of {count}","panel.screen.position":"Estimated position","panel.screen.progress":"Positioning progress","panel.toast.action.undo":"Undo","panel.toast.assigned":"{count} assignments applied","panel.toast.assigned_one":"1 assignment applied","panel.toast.measure_removed":"Measurement removed: «{cover}» now uses {destination}.","panel.toast.order_saved":"The new order will be remembered.","panel.toast.profile_deleted":"Profile «{profile}» deleted: the covers go back to the file or to the defaults.","panel.toast.profile_renamed":"Renamed to «{profile}»: the rename follows every cover that uses it.","panel.toast.profile_saved":"Profile «{profile}» updated: {count} covers reached.","panel.toast.profile_saved_one":"Profile «{profile}» updated: 1 cover reached.","panel.toast.travel_saved":"The travel of «{cover}» is saved: the profile is brought to this measurement.","panel.toast.undone":"Changes undone: everything as it was.","panel.toast.values_saved":"The values of «{cover}» are saved: they beat the profile and the file."};var st=Dt,Qn=Object.keys(st);var pn=/^\/myhome_static\/[A-Za-z0-9._~\-/]+$/,dn=/(^|\/)\.\.?(\/|$)/,at=n=>pn.test(n)&&!dn.test(n),zt=/^[A-Za-z0-9 %.,\-]+$/,Ht=n=>{if(!at(n.src))return null;let t=n.size&&zt.test(n.size)?n.size:"100% auto",e=n.pos&&zt.test(n.pos)?n.pos:"50% 60%";return{backgroundImage:`url("${n.src}")`,backgroundSize:t,backgroundPosition:e}};var cn=/^!\[([^\]]*)\]\(([^)\s]+)\)$/;var we=n=>{let t=[],e=n.split("**"),i=e.length%2===0;return e.forEach((r,o)=>{if(!r)return;let s=o%2===1&&!(i&&o===e.length-1);t.push(s?a`<strong>${r}</strong>`:a`<span>${r}</span>`)}),t},hn=n=>/^\s*[-*]\s+/.test(n),Y=n=>{let t=(n||"").replace(/\r\n/g,`
`).split(/\n{2,}/),e=[];for(let i of t){let r=i.trim();if(!r)continue;let o=cn.exec(r);if(o){e.push(at(o[2])?a`<img class="md-image" src=${o[2]} alt=${o[1]} />`:a`<p>${we(o[1])}</p>`);continue}let s=r.split(`
`);if(s.every(hn)){e.push(a`<ul>
          ${s.map(p=>a`<li>${we(p.replace(/^\s*[-*]\s+/,""))}</li>`)}
        </ul>`);continue}e.push(a`<p>
        ${s.map((p,d)=>d===0?we(p):[a`<br />`,...we(p)])}
      </p>`)}return a`${e}`};var A=n=>n&&typeof n=="object"&&"code"in n?n:{code:"unknown_error",message:String(n)},Ft=(n,t)=>n.sendMessagePromise({type:"myhome/calibration/overview",...t?{entry_id:t}:{}}),Nt=(n,t)=>n.sendMessagePromise({type:"myhome/calibration/texts",language:t}),qt=(n,t,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_detail",entry_id:t,cover_unique_id:e}),be=(n,t,e,i)=>n.sendMessagePromise({type:"myhome/calibration/preview",entry_id:t,items:e,...i?{profile_values:i}:{}}),Ut=(n,t,e)=>n.subscribeMessage(e,{type:"myhome/calibration/subscribe",...t?{entry_id:t}:{}}),ae=n=>A(n).code==="unknown_command",Wt=(n,t,e,i)=>n.sendMessagePromise({type:"myhome/calibration/assign",entry_id:t,assignments:e,...i?{order:i}:{}}),Bt=(n,t,e,i)=>n.sendMessagePromise({type:"myhome/calibration/reorder",entry_id:t,order:e,...i!==void 0?{profile:i}:{}}),Kt=(n,t,e,i)=>n.sendMessagePromise({type:"myhome/calibration/set_travel",entry_id:t,cover_unique_id:e,height:i}),Gt=(n,t,e,i,r)=>n.sendMessagePromise({type:"myhome/calibration/cover_edit",entry_id:t,cover_unique_id:e,overrides:i,...r!==void 0?{height:r}:{}}),jt=(n,t,e)=>n.sendMessagePromise({type:"myhome/calibration/cover_forget",entry_id:t,cover_unique_id:e}),Vt=(n,t,e,i,r)=>n.sendMessagePromise({type:"myhome/calibration/profile_edit",entry_id:t,name:e,values:i,reference_height:r}),Yt=(n,t,e,i)=>n.sendMessagePromise({type:"myhome/calibration/profile_rename",entry_id:t,name:e,new_name:i}),Xt=(n,t,e)=>n.sendMessagePromise({type:"myhome/calibration/profile_delete",entry_id:t,name:e}),Zt=(n,t,e)=>n.sendMessagePromise({type:"myhome/calibration/undo",entry_id:t,undo_token:e});var mn=/\{([A-Za-z0-9_]+)\}/g,ye=(n,t)=>t?n.replace(mn,(e,i)=>Object.prototype.hasOwnProperty.call(t,i)?String(t[i]):e):n,un=/[“”„"‹›«»][\s  ]*(\{[A-Za-z0-9_]+\})[\s  ]*[“”„"‹›«»]/gu,Qt=n=>n.replace(un,"«$1»"),y=class{constructor(){this._texts={};this._numbers=new Map;this._dates=null;this.language="en";this.loaded=!1}async load(t,e){let i=await Nt(t,e);this._texts=i.texts??{},this.language=i.language,this.loaded=!0,this._numbers.clear(),this._dates=null}t(t,e){let i=this._lookup(t);if(i!==null)return ye(i,e);let r=st[t];return ye(r??t,e)}md(t,e){return Y(this.t(t,e))}refusal(t,e){let i=t?this._lookup(`exceptions.${t}.message`):null;return i!==null?ye(Qt(i),e):this.t("panel.error.not_found")}origin(t,e){let i=`selector.calibration_origin.options.${t}`;return ye(Qt(this._lookup(i)??i),{profile:e??""})}number(t,e){let i=this._numbers.get(e);return i||(i=new Intl.NumberFormat(this.language,{minimumFractionDigits:e,maximumFractionDigits:e}),this._numbers.set(e,i)),i.format(t)}date(t){let e=new Date(t);return Number.isNaN(e.getTime())?t:(this._dates||(this._dates=new Intl.DateTimeFormat(this.language,{dateStyle:"long"})),this._dates.format(e))}_lookup(t){let e=this._texts;for(let i of t.split(".")){if(e===null||typeof e!="object")return null;e=e[i]}return typeof e=="string"?e:null}};var Jt=n=>typeof customElements<"u"&&customElements.get(n)!==void 0;var ei=n=>{n.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var xe=(n,t)=>{let e=$e(n.unique_id,t);return e?e.to:n.profile??null},$e=(n,t)=>t.find(e=>e.cover===n),ti=(n,t)=>t===null?n.t("panel.assign.target_none"):n.t("panel.assign.pending.route_name",{profile:t}),ii=(n,t,e)=>n.t("panel.assign.pending.route",{from:ti(n,t),to:ti(n,e)}),ni=(n,t,e)=>{let i=n.filter(r=>r.cover!==t.unique_id);return e===(t.profile??null)?{pending:i,withdrawn:!0}:{pending:[...i,{cover:t.unique_id,to:e}],withdrawn:!1}},ri=(n,t)=>{let e=new Map(n.covers.map(o=>[o.unique_id,o]));if(!t)return[...n.covers].sort((o,s)=>o.order_index-s.order_index);let i=new Set,r=[];for(let o of t){let s=e.get(o);s&&!i.has(o)&&(i.add(o),r.push(s))}for(let o of n.covers)i.has(o.unique_id)||r.push(o);return r},lt=(n,t,e)=>{let i=n.filter(o=>o!==t),r=i.length;if(e.beforeId){let o=i.indexOf(e.beforeId);r=o<0?i.length:o}else if(e.afterId){let o=i.indexOf(e.afterId);r=o<0?i.length:o+1}return[...i.slice(0,r),t,...i.slice(r)]},oi=(n,t,e)=>{let i=e.filter(r=>r!==t).at(-1)??null;return lt(n,t,{beforeId:null,afterId:i})},pt=(n,t,e)=>{let i=new Set(e.map(r=>r.unique_id));return n.filter(r=>i.has(r.cover)).map(r=>{let o=t[r.cover],s=o===void 0?void 0:I(o);return{cover_unique_id:r.cover,profile:r.to,...s==null?{}:{height:s}}})},I=n=>{let t=n.trim().replace(",",".");if(!t)return null;let e=Number(t);return Number.isFinite(e)?e:null},vn=20,gn=500,le=n=>{if(n===void 0||n.trim()==="")return"missing_travel";let t=I(n);return t===null?"not_a_number":t<vn||t>gn?"out_of_range":null},dt=n=>({cover_unique_id:n.unique_id,profile:n.profile_from_file?null:n.profile??null}),si=(n,t)=>t.to!==null&&n.height===null,M=["opening_time","closing_time","slat_time","opening_roll","closing_roll"],pe=["opening_time","closing_time","slat_time"],de=["opening_roll","closing_roll"],ke=["slat_time",...de],L={opening_time:1,closing_time:1,slat_time:1,opening_roll:2,closing_roll:2};var O={opening_time:{min:1,max:600,decimals:1},closing_time:{min:1,max:600,decimals:1},slat_time:{min:0,max:60,decimals:1},opening_roll:{min:1,max:5,decimals:2},closing_roll:{min:1,max:5,decimals:2},height:{min:20,max:500,decimals:0},reference_height:{min:20,max:500,decimals:0}},X={opening_time:"panel.common.unit.seconds",closing_time:"panel.common.unit.seconds",slat_time:"panel.common.unit.seconds",opening_roll:null,closing_roll:null,height:"panel.common.unit.centimetres",reference_height:"panel.common.unit.centimetres"},z=n=>n.replace(/\s*\([^()]*\)\s*$/u,""),W=(n,t)=>t?`${n} ${t}`:n,b=(n,t)=>{let e=(t??"").trim();if(e==="")return null;let i=I(e);if(i===null)return"not_a_number";let r=O[n];return r&&(i<r.min||i>r.max)?"out_of_range":null},$=n=>(n??"").trim()==="";var k="/config/integrations/integration/myhome";var ct="dialog-data-entry-flow",fn=()=>typeof customElements<"u"&&customElements.get(ct)!==void 0,ai=n=>{history.pushState(null,"",n),window.dispatchEvent(new CustomEvent("location-changed",{detail:{replace:!1}}))},li=n=>fn()?(n.source.dispatchEvent(new CustomEvent("show-dialog",{bubbles:!0,composed:!0,detail:{dialogTag:ct,dialogImport:()=>Promise.resolve(),dialogParams:{startFlowHandler:n.entryId,domain:"myhome"}}})),setTimeout(()=>{document.querySelector(ct)||(n.onLeaving(),ai(k))},400),"waiting"):(n.onLeaving(),ai(k),"page");var B=n=>n.view==="cover"||n.view==="profile",pi=(n,t,e)=>!B(e)||!B(t)?null:t.path===e.path?n:n&&n.path===e.path?null:t,di=n=>n?.path??"/";var _n={view:"overview",params:{},path:"/"},ci=n=>{let t="/"+(n||"").replace(/^#/,"").replace(/^\/+/,"").replace(/\/+$/,"");if(t==="/")return _n;let e=t.slice(1).split("/"),i=e.slice(1).join("/"),r=i;try{r=decodeURIComponent(i)}catch{}return e[0]==="cover"&&i?{view:"cover",params:{id:r},path:t}:e[0]==="profile"&&i?{view:"profile",params:{name:r},path:t}:e[0]==="calibrate"&&i?{view:"calibrate",params:{session:r},path:t}:{view:"unknown",params:{},path:t}};var Se=class{constructor(){this._onChange=()=>{};this._fromHost="/";this._listener=()=>this._emit()}start(t){this._onChange=t,window.addEventListener("hashchange",this._listener)}stop(){window.removeEventListener("hashchange",this._listener),this._onChange=()=>{}}setHostPath(t){let e=t||"/";if(e===this._fromHost)return;let i=this.current.path;this._fromHost=e,this.current.path!==i&&this._emit()}get current(){let t=typeof location<"u"?location.hash:"";return t&&t.length>1?ci(t.slice(1)):ci(this._fromHost)}navigate(t){let e="#"+(t.startsWith("/")?t:"/"+t);location.hash!==e&&(location.hash=e)}_emit(){this._onChange(this.current)}};var ce={for:null,answer:null,loading:!1,error:null,mode:"view",form:{},errors:{},preview:null,previewing:!1},he={for:null,mode:"view",form:{},errors:{},newName:"",nameError:"",impact:null,impacting:!1},K=n=>({entryId:null,overview:null,status:"loading",error:null,connection:"starting",route:n,search:"",room:"",announce:"",pending:[],order:null,drag:null,armed:null,dialog:null,review:!1,heights:{},heightsForced:!1,showAll:!1,preview:null,previewing:!1,applying:!1,snack:null,writeError:null,detail:ce,profile:he,session:null,sessionError:null,wizardIntent:null,clientId:""}),Ee={pending:[],order:null,heights:{},heightsForced:!1,preview:null,previewing:!1,review:!1,writeError:null},Re=class{constructor(t){this._subscribers=new Set;this._state=K(t)}get state(){return this._state}subscribe(t){return this._subscribers.add(t),()=>this._subscribers.delete(t)}set(t){this._state={...this._state,...t};for(let e of this._subscribers)e(this._state)}setOverview(t){this.set({overview:t,entryId:t.entry_id,status:"ready",error:null})}setError(t){this.set({status:"error",error:t})}announce(t){this.set({announce:""}),this.set({announce:t})}};var S=m`:host{--myhome-text-on-primary: var(--text-primary-color, #ffffff);--myhome-snack-action: var( --snack-action-color, color-mix(in srgb, var(--myhome-accent) 40%, var(--myhome-background)) );--myhome-primary: var(--primary-color, #03a9f4);--myhome-accent: var(--accent-color, #ff9800);--myhome-text: var(--primary-text-color, #212121);--myhome-text-soft: var(--secondary-text-color, #727272);--myhome-text-off: var(--disabled-text-color, #bdbdbd);--myhome-background: var(--primary-background-color, #fafafa);--myhome-background-soft: var(--secondary-background-color, #e5e5e5);--myhome-card: var(--card-background-color, #ffffff);--myhome-divider: var(--divider-color, rgba(0, 0, 0, .12));--myhome-error: var(--error-color, #db4437);--myhome-warning: var(--warning-color, #ffa600);--myhome-success: var(--success-color, #43a047);--myhome-info: var(--info-color, #039be5);--myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));--myhome-header-text: var(--app-header-text-color, #ffffff);--myhome-radius: var(--ha-card-border-radius, 12px);--myhome-shadow: var(--ha-card-box-shadow, 0 1px 4px rgba(0, 0, 0, .14));--myhome-primary-pastel: color-mix(in srgb, var(--myhome-primary) 20%, var(--myhome-card));--myhome-primary-faint: color-mix(in srgb, var(--myhome-primary) 10%, var(--myhome-card));--myhome-accent-pastel: color-mix(in srgb, var(--myhome-accent) 18%, var(--myhome-card));--myhome-error-pastel: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));--myhome-error-strong: color-mix(in srgb, var(--myhome-error) 14%, var(--myhome-card));--myhome-warning-pastel: color-mix(in srgb, var(--myhome-warning) 12%, var(--myhome-card));--myhome-success-pastel: color-mix(in srgb, var(--myhome-success) 12%, var(--myhome-card));--myhome-info-pastel: color-mix(in srgb, var(--myhome-info) 12%, var(--myhome-card));--myhome-primary-ink: color-mix(in srgb, var(--myhome-primary) 50%, var(--myhome-text));--myhome-error-ink: color-mix(in srgb, var(--myhome-error) 50%, var(--myhome-text));--myhome-warning-ink: color-mix(in srgb, var(--myhome-warning) 50%, var(--myhome-text));--myhome-success-ink: color-mix(in srgb, var(--myhome-success) 50%, var(--myhome-text));--myhome-info-ink: color-mix(in srgb, var(--myhome-info) 50%, var(--myhome-text));--myhome-text-soft-ink: color-mix(in srgb, var(--myhome-text-soft) 50%, var(--myhome-text));--myhome-field-border: color-mix(in srgb, var(--myhome-text-soft) 80%, var(--myhome-card));--myhome-drawing-paper: var(--myhome-drawing-surface, #ffffff);display:block;min-height:100%;color:var(--myhome-text);background:var(--myhome-background)}*,*:before,*:after{box-sizing:border-box}:host * :focus-visible{outline:2px solid var(--myhome-primary-ink);outline-offset:2px}@media(prefers-reduced-motion:reduce){:host *{animation-duration:.001ms!important;transition-duration:.001ms!important}}`,R=m`.card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}`,E=m`.cta{min-height:48px;padding:0 24px;border-radius:24px;border:none;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font:inherit;font-size:15px;font-weight:500;cursor:pointer}.cta.secondary{background:transparent;border:1px solid var(--myhome-primary-ink);color:var(--myhome-primary-ink)}.cta.text{background:transparent;border:none;color:var(--myhome-primary-ink);padding:0 12px}.cta.destructive{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}.cta[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.cta.compact{min-height:44px;padding:0 18px;border-radius:22px;font-size:14px}`,H=m`.field{height:44px;border-radius:8px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:var(--myhome-text);padding:0 12px;font:inherit;font-size:14px}.field:disabled{color:var(--myhome-text-off)}`,Pe=m`.sr-only{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0}`;var mi=n=>a`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${n}</div>`,G=n=>{requestAnimationFrame(()=>{let t=n();t&&t.focus()})};var Z=class{constructor(){this._root=null;this._onKey=t=>{if(t.key!=="Tab"||!this._root)return;let e=hi(this._root);if(e.length===0){t.preventDefault(),this._root.focus();return}let i=e[0],r=e[e.length-1],o=ht(this._root.getRootNode());t.shiftKey&&(o===i||o===this._root)?(t.preventDefault(),r.focus()):!t.shiftKey&&o===r&&(t.preventDefault(),i.focus())}}hold(t,e=!0){this.release(),this._root=t,t.addEventListener("keydown",this._onKey),e&&G(()=>hi(t)[0]??t)}release(){this._root?.removeEventListener("keydown",this._onKey),this._root=null}},wn='a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',hi=n=>{let t=[],e=i=>{for(let r of i.querySelectorAll("*"))r.matches(wn)&&t.push(r),r.shadowRoot&&e(r.shadowRoot)};return e(n),t.filter(i=>i.offsetParent!==null)},ht=n=>{let t=n.activeElement;for(;t?.shadowRoot?.activeElement;)t=t.shadowRoot.activeElement;return t};var Te=m`.sheet-backdrop{position:fixed;inset:0;background:#0006;z-index:50}.sheet{position:fixed;left:0;right:0;bottom:0;max-height:86vh;background:var(--myhome-card);color:var(--myhome-text);z-index:51;border-radius:16px 16px 0 0;box-shadow:var(--myhome-shadow);display:flex;flex-direction:column}@media(min-width:600px){.sheet{inset:0 0 0 auto;width:min(480px,100vw);max-height:none;border-radius:0}}.sheet .head{display:flex;align-items:center;gap:8px;padding:12px 16px;border-bottom:1px solid var(--myhome-divider)}.sheet .head h2{margin:0;font-size:18px;font-weight:500;flex:1;min-width:0}.sheet .head button{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);font-size:20px;cursor:pointer;border-radius:24px}.sheet .body{flex:1;overflow:auto;padding:16px;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}`;var ui=[Te,m`.sheet .head h2.named{font-size:19px;font-weight:700;color:var(--myhome-primary);overflow-wrap:anywhere}.sheet.drawer .body{padding:16px 16px 0;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px));background:var(--myhome-background)}`],vi=n=>{let{i18n:t}=n,e=()=>{n.applying||n.onClose()};return a`
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
          aria-label=${n.hasBack?t.t("panel.common.action.back"):t.t("panel.common.action.close")}
          title=${n.hasBack?t.t("panel.common.action.back"):t.t("panel.common.action.close")}
          ?disabled=${n.applying}
          @click=${e}
        >
          ${n.hasBack?"←":"✕"}
        </button>
        <h2 id="drawer-title" class="named">${n.title}</h2>
      </div>
      <div class="body">${n.content}</div>
    </div>
  `};var gi=m`.measuring{max-width:1200px;margin:16px auto 0;padding:12px 16px;border-radius:var(--myhome-radius);background:var(--myhome-warning-pastel);display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.measuring strong{color:var(--myhome-warning-ink);font-weight:500}.measuring .body{flex:1 1 320px;line-height:1.5}.measuring .links{display:flex;gap:16px}.measuring a{color:var(--myhome-primary-ink);min-height:44px;display:inline-flex;align-items:center}`,fi=(n,t,e)=>a`<div class="measuring" role="status" aria-live="polite">
    <strong>${n.t("panel.banner.measuring.title")}</strong>
    <span class="body">${n.t("panel.banner.measuring.body",{cover:t})}</span>
    <span class="links">
      <a href=${e}>${n.t("panel.banner.measuring.action.resume")}</a>
      <a href=${e}>${n.t("panel.banner.measuring.action.stop")}</a>
    </span>
  </div>`;var _i={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},wi=n=>(...t)=>({_$litDirective$:n,values:t}),Ce=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,i){this._$Ct=t,this._$AM=e,this._$Ci=i}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var bi="important",bn=" !"+bi,Ae=wi(class extends Ce{constructor(n){if(super(n),n.type!==_i.ATTRIBUTE||n.name!=="style"||n.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(n){return Object.keys(n).reduce((t,e)=>{let i=n[e];return i==null?t:t+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${i};`},"")}update(n,[t]){let{style:e}=n.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(t)),this.render(t);for(let i of this.ft)t[i]==null&&(this.ft.delete(i),i.includes("-")?e.removeProperty(i):e[i]=null);for(let i in t){let r=t[i];if(r!=null){this.ft.add(i);let o=typeof r=="string"&&r.endsWith(bn);i.includes("-")||o?e.setProperty(i,o?r.slice(0,-11):r,o?bi:""):e[i]=r}}return C}});var Ie=m`.sk{--sk-base: var(--myhome-background-soft)}.sk-bar{height:12px;border-radius:6px;background:linear-gradient(90deg,var(--sk-base) 25%,var(--myhome-card) 50%,var(--sk-base) 75%);background-size:400% 100%;animation:sk-slide 1.4s linear infinite}@keyframes sk-slide{0%{background-position:100% 0}to{background-position:0 0}}.sk-intro{max-width:72ch;margin:8px 0 16px;display:flex;flex-direction:column;gap:8px}.sk-controls{display:flex;gap:12px;margin:0 0 16px}.sk-controls .sk-bar{height:44px;border-radius:8px}.sk-groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.sk-groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(300px,1fr);align-items:start}}.sk-group{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.sk-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider);display:flex;flex-direction:column;gap:8px}.sk-body{padding:8px;display:flex;flex-direction:column;gap:2px}.sk-row{min-height:48px;padding:8px;display:flex;flex-direction:column;gap:8px;justify-content:center}.sk-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:0 0 16px;max-width:720px;display:flex;flex-direction:column;gap:12px}`,v=(n,t)=>a`<div
    class="sk-bar"
    aria-hidden="true"
    style=${Ae(t?{width:n,height:t}:{width:n})}
  ></div>`,mt=()=>a`<div class="sk-row">${v("62%")}${v("40%","10px")}${v("28%","18px")}</div>`,yi=()=>a`<div class="sk-group">
    <div class="sk-head">${v("45%","16px")}${v("80%","10px")}${v("60%","10px")}</div>
    <div class="sk-body">${mt()}${mt()}${mt()}</div>
  </div>`,xi=n=>a`<div class="sk" role="status" aria-busy="true" aria-label=${n.t("panel.common.loading")}>
    <div class="sk-intro">${v("92%","14px")}${v("74%","14px")}${v("36%","12px")}</div>
    <div class="sk-controls">${v("300px")}${v("160px")}</div>
    <div class="sk-groups">${yi()}${yi()}</div>
  </div>`,Me=n=>a`<div class="sk" role="status" aria-busy="true" aria-label=${n.t("panel.common.loading")}>
    <div class="sk-card">
      ${v("40%","16px")}${v("70%","10px")}${v("100%")}${v("100%")}${v("55%")}
    </div>
    <div class="sk-card">${v("35%","16px")}${v("100%","44px")}${v("100%","44px")}</div>
  </div>`;var Le=m`.strip{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translate(-50%);max-width:92vw;box-sizing:border-box;box-shadow:var(--myhome-shadow)}.strip.drop-zone{z-index:45;padding:14px 28px;min-height:48px;display:flex;align-items:center;border-radius:24px;font-size:14px;font-weight:500;border:2px dashed var(--myhome-divider);background:var(--myhome-card);color:var(--myhome-text-soft)}.strip.drop-zone.over{border:2px solid var(--myhome-primary-ink);color:var(--myhome-primary-ink)}.strip.dark{background:var(--myhome-text);color:var(--myhome-background);border-radius:8px;font-size:14px}.strip.armed{z-index:40;padding:10px 16px;display:flex;gap:16px;align-items:center;width:max-content}.strip.armed .what{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;min-width:0}.strip.applying{z-index:70;padding:12px 20px}.strip.applying .under{display:block;font-size:12px;opacity:.75;margin-top:2px}.strip.snack{z-index:70;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:8px}.strip.dark button{min-height:44px;padding:0 12px;border:none;background:transparent;color:var(--myhome-snack-action);font:inherit;font-weight:500;cursor:pointer}.pending-bar{z-index:30;background:var(--myhome-card);border:1px solid var(--myhome-divider);border-radius:28px;padding:8px 8px 8px 20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}.pending-bar .count{font-size:14px}.pending-bar .locked{font-size:13px;color:var(--myhome-warning-ink);flex-basis:100%}.pending-bar button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.pending-bar .discard{padding:0 12px;background:transparent;color:var(--myhome-text-soft)}.pending-bar .review{padding:0 20px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.pending-bar button[disabled]{color:var(--myhome-text-off);background:var(--myhome-background-soft);cursor:default}@media(max-width:599px){.strip.pending-bar{left:8px;right:8px;transform:none;max-width:none;justify-content:space-between}.strip.pending-bar .count{flex-basis:100%}}`,$i=(n,t)=>a`<div class="strip drop-zone ${t?"over":""}" data-group="none">
    ${n.t("panel.assign.drop_zone")}
  </div>`,ki=(n,t,e)=>a`<div class="strip dark armed" role="status">
    <span class="what" title=${t}>${n.t("panel.assign.armed",{cover:t})}</span>
    <button type="button" @click=${e}>${n.t("panel.common.action.cancel")}</button>
  </div>`,Si=n=>{let{i18n:t}=n;return a`<div class="strip pending-bar">
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
    ${n.locked?a`<span class="locked"
          >${t.t("panel.banner.measuring.body",{cover:n.lockedCover})}</span
        >`:l}
  </div>`},Oe=n=>a`<div class="strip dark applying" role="status">
    ${n.t("panel.banner.applying.title")}
    <span class="under">${n.t("panel.banner.applying.body")}</span>
  </div>`,De=(n,t,e)=>a`<div class="strip dark snack" role="status">
    <span>${t}</span>
    ${e?a`<button type="button" @click=${e}>
          ${n.t("panel.toast.action.undo")}
        </button>`:l}
  </div>`;var Ri=n=>{let t=new Map;for(let e of n.querySelectorAll("[data-row]")){let i=e.getBoundingClientRect();t.set(e.getAttribute("data-row")??"",{top:i.top,left:i.left})}return t},Ei=(n,t)=>{if(!yn())for(let e of n.querySelectorAll("[data-row]")){let i=t.get(e.getAttribute("data-row")??"");if(!i)continue;let r=e.getBoundingClientRect(),o=i.left-r.left,s=i.top-r.top;if(Math.abs(o)<1&&Math.abs(s)<1)continue;e.style.transition="none",e.style.transform=`translate(${o}px, ${s}px)`,e.offsetHeight,e.style.transition="transform 220ms ease",e.style.transform="";let p=()=>{e.style.transition="",e.removeEventListener("transitionend",p)};e.addEventListener("transitionend",p)}},yn=()=>typeof matchMedia=="function"&&matchMedia("(prefers-reduced-motion: reduce)").matches;var ze=class{constructor(t){this._start=null;this._longPress=null;this._pressedAt=null;this._ghost=null;this._target=null;this._scroll=null;this._edge=0;this._scroller=null;this._clearLongPressOnce=()=>this._clearLongPress();this._onPressMove=t=>{let e=this._pressedAt;e&&Math.hypot(t.clientX-e.x,t.clientY-e.y)<12||this._clearLongPress()};this._onMove=t=>{let e=this._start;if(!e)return;if(!e.live){if(Math.hypot(t.clientX-e.x,t.clientY-e.y)<6)return;e.live=!0,this._callbacks.onStart(e.cover)}this._moveGhost(t.clientX,t.clientY),this._autoScroll(t.clientX,t.clientY);let i=this._targetAt(t.clientX,t.clientY,e.cover);xn(i,this._target)||(this._target=i,this._callbacks.onOver(i))};this._onUp=()=>this._finish(!0);this._onCancel=()=>this._finish(!1);this._callbacks=t}get dragging(){return this._start?.live?this._start.cover:null}press(t,e){if(!this._callbacks.blocked()){if(this._callbacks.narrow()){this._arm(t,e);return}e.preventDefault(),this._start={cover:t,x:e.clientX,y:e.clientY,live:!1},window.addEventListener("pointermove",this._onMove),window.addEventListener("pointerup",this._onUp),window.addEventListener("pointercancel",this._onCancel),window.addEventListener("blur",this._onCancel)}}arm(t,e){this._callbacks.blocked()||this._arm(t,e)}cancel(){if(this._start?.live){this._finish(!1);return}this._clear()}stop(){this._clear(),this._clearLongPress()}_arm(t,e){this._clearLongPress(),this._pressedAt=e?{x:e.clientX,y:e.clientY}:null,this._longPress=setTimeout(()=>{this._longPress=null,this._callbacks.onArm(t)},450),window.addEventListener("pointerup",this._clearLongPressOnce),window.addEventListener("pointermove",this._onPressMove),window.addEventListener("pointercancel",this._clearLongPressOnce),window.addEventListener("blur",this._clearLongPressOnce)}_clearLongPress(){this._longPress&&(clearTimeout(this._longPress),this._longPress=null),this._pressedAt=null,window.removeEventListener("pointerup",this._clearLongPressOnce),window.removeEventListener("pointermove",this._onPressMove),window.removeEventListener("pointercancel",this._clearLongPressOnce),window.removeEventListener("blur",this._clearLongPressOnce)}_finish(t){let e=this._start?.live??!1;this._clear(),e&&this._callbacks.onEnd(t)}_clear(){window.removeEventListener("pointermove",this._onMove),window.removeEventListener("pointerup",this._onUp),window.removeEventListener("pointercancel",this._onCancel),window.removeEventListener("blur",this._onCancel),this._start=null,this._target=null,this._stopScrolling(),this._ghost?.remove(),this._ghost=null}ghost(t,e){let i=document.createElement("div");i.className="drag-ghost",i.setAttribute("aria-hidden","true"),i.textContent=t,e.appendChild(i),this._ghost=i}_moveGhost(t,e){this._ghost&&(this._ghost.style.transform=`translate(${t+12}px, ${e+8}px)`)}_autoScroll(t,e){let i=this._callbacks.root().querySelector(".groups");if(!i||i.scrollWidth<=i.clientWidth){this._stopScrolling();return}let r=i.getBoundingClientRect(),o=t<r.left+64?-1:t>r.right-64?1:0;if(this._edge=o,this._scroller=i,o===0){this._stopScrolling();return}if(this._scroll===null){let s=()=>{this._edge===0||!this._scroller||(this._scroller.scrollLeft+=this._edge*14,this._scroll=requestAnimationFrame(s))};this._scroll=requestAnimationFrame(s)}}_stopScrolling(){this._edge=0,this._scroll!==null&&(cancelAnimationFrame(this._scroll),this._scroll=null)}_targetAt(t,e,i){let r=this._callbacks.root().elementFromPoint(t,e),o=r?.closest?.("[data-group]");if(!o)return null;let s=o.getAttribute("data-group")??"",p=r?.closest?.("[data-row]"),d=p?.getAttribute("data-row")??null;if(!p||!d||d===i)return{group:s,beforeId:null,afterId:null,end:!0};let c=p.getBoundingClientRect();return e<c.top+c.height/2?{group:s,beforeId:d,afterId:null,end:!1}:{group:s,beforeId:null,afterId:d,end:!1}}},xn=(n,t)=>n===null||t===null?n===t:n.group===t.group&&n.beforeId===t.beforeId&&n.afterId===t.afterId;var He=m`.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;display:inline-flex;align-items:center;gap:5px;background:var(--myhome-background-soft);color:var(--myhome-text-soft-ink)}.chip.measured{background:var(--myhome-primary-pastel);color:var(--myhome-text);box-shadow:inset 0 0 0 1px var(--myhome-primary)}.chip.adjusted{background:var(--myhome-accent-pastel);color:var(--myhome-text)}.chip .dot{width:6px;height:6px;border-radius:3px;background:var(--myhome-accent);display:inline-block}`,Fe=(n,t,e,i)=>{let r=t==="measured"?"measured":t==="adjusted"?"adjusted":"neutral",o;return i&&t==="inherited"?o=n.t("panel.overview.cover.origin_inherited"):i&&t==="adjusted"?o=n.t("panel.overview.cover.origin_adjusted"):o=n.origin(t,e),a`<span class="chip ${r}"
    >${r==="adjusted"?a`<span class="dot" aria-hidden="true"></span>`:l}${o}</span
  >`};var Pi=m`.row{position:relative;display:flex;align-items:flex-start;gap:8px;padding:8px;border-radius:8px;min-height:48px;-webkit-user-select:none;-webkit-touch-callout:none}.row .divider{position:absolute;left:8px;right:8px;top:-1px;height:1px;background:var(--myhome-divider);opacity:.6;pointer-events:none}.row .insert-line{position:absolute;left:8px;right:8px;top:-2px;height:3px;border-radius:2px;background:var(--myhome-primary-ink);pointer-events:none}.row .pending-outline{position:absolute;inset:0;border:2px dashed var(--myhome-primary-ink);border-radius:8px;pointer-events:none}.row .source-veil{position:absolute;inset:0;background:var(--myhome-background-soft);opacity:.7;border-radius:8px;pointer-events:none}.row .handle{width:48px;height:48px;flex:0 0 48px;border:none;background:transparent;color:var(--myhome-text-soft);cursor:grab;font-size:18px;letter-spacing:2px;border-radius:8px;touch-action:none;-webkit-user-select:none;user-select:none}.row .handle[disabled]{cursor:default;color:var(--myhome-text-off)}@media(max-width:599px){.row .handle{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.row .handle:focus-visible{position:static;width:48px;height:48px;margin:0;overflow:visible;clip-path:none}}.row .body{flex:1 1 auto;min-width:0}.row .main{display:block;width:100%;text-align:left;border:none;background:transparent;color:inherit;font:inherit;cursor:pointer;padding:2px 0;border-radius:6px}.row .name{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:14.5px;line-height:1.35}.row .sub{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.row .chips:empty{display:none}.row .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}.row .warn{display:block;font-size:12.5px;color:var(--myhome-warning-ink);margin-top:4px}.route{display:inline-flex;align-items:center;gap:2px;font-size:12px;color:var(--myhome-primary-ink);background:var(--myhome-primary-faint);border:1px dashed var(--myhome-primary-ink);border-radius:10px;padding:2px 2px 2px 8px;max-width:100%}.route .text{min-width:0;overflow-wrap:anywhere}.route .withdraw{width:48px;height:48px;margin:-14px -14px -14px 0;display:inline-flex;align-items:center;justify-content:center;border:none;background:transparent;color:inherit;font:inherit;font-size:14px;line-height:1;cursor:pointer;border-radius:24px}.row .note{display:block;font-size:12.5px;color:var(--myhome-info-ink);margin-top:4px}`,$n=(n,t,e)=>{let i=t.height!==null?n.t("panel.overview.cover.travel",{travel:n.number(t.height,0)}):e?n.t("panel.overview.cover.travel_needed"):n.t("panel.overview.cover.travel_unknown");return t.area?`${t.area} · ${i}`:i},kn=(n,t)=>t.has_own.length===0?"":M.every(e=>t.has_own.includes(e))?n.t("panel.assign.pending.all_own"):n.t("panel.assign.pending.some_own"),Ti=(n,t)=>{let{i18n:e,pending:i}=t,r=!!i&&i.to!==null&&n.height===null,o=i?kn(e,n):"",s=`chips-${n.unique_id}`;return a`<div class="row" data-row=${n.unique_id}>
    ${t.insertBefore?a`<div class="insert-line" aria-hidden="true"></div>`:t.first?l:a`<div class="divider" aria-hidden="true"></div>`}
    ${i?a`<div class="pending-outline" aria-hidden="true"></div>`:l}
    ${t.dragging?a`<div class="source-veil" aria-hidden="true"></div>`:l}
    <button
      class="handle"
      type="button"
      ?disabled=${t.locked}
      aria-label=${e.t("panel.assign.handle",{cover:n.name})}
      title=${t.locked?e.t("panel.banner.measuring.title"):e.t("panel.assign.handle_hint")}
      @pointerdown=${p=>t.onGrab(n,p)}
      @click=${p=>p.stopPropagation()}
      @keydown=${p=>{(p.key==="Enter"||p.key===" ")&&(p.preventDefault(),t.locked||t.onPick(n))}}
    >
      ⠿
    </button>
    <div
      class="body"
      @pointerdown=${p=>t.onRowPress(n,p)}
    >
      <button class="main" type="button" title=${n.name} aria-describedby=${s}
        @click=${()=>t.onOpen(n)}>
        <span class="name">${n.name}</span>
        <span class="sub">${$n(e,n,r)}</span>
        ${o?a`<span class="note">${o}</span>`:l}
        ${n.profile_missing?a`<span class="warn"
              >${e.t("panel.overview.cover.profile_missing",{profile:n.profile??""})}</span
            >`:l}
      </button>
      <div class="chips" id=${s}>
        ${Fe(e,n.origin,n.profile,t.short)}
        ${i?a`<span class="route">
              <span class="text">${t.route}</span>
              <button
                class="withdraw"
                type="button"
                aria-label=${e.t("panel.assign.action.withdraw")}
                title=${e.t("panel.assign.action.withdraw")}
                @pointerdown=${p=>p.stopPropagation()}
                @click=${()=>t.onWithdraw(n)}
              >
                ✕
              </button>
            </span>`:l}
      </div>
    </div>
  </div>`};var Ci=m`.backdrop{position:fixed;inset:0;background:#0006;z-index:60}.dialog{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:min(440px,92vw);max-height:80vh;overflow:auto;background:var(--myhome-card);color:var(--myhome-text);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);z-index:61;padding:20px;box-sizing:border-box}.dialog h2{margin:0 0 4px;font-size:18px;font-weight:500}.dialog .subtitle{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft)}.dialog .options{display:flex;flex-direction:column;gap:8px}.dialog .option{text-align:left;border-radius:8px;font:inherit;padding:12px;min-height:48px;cursor:pointer;border:1px solid var(--myhome-field-border);background:transparent;color:inherit}.dialog .option.current{border-color:var(--myhome-primary-ink);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.dialog .option .line{display:flex;align-items:baseline;gap:8px}.dialog .option .title{font-weight:500;flex:1}.dialog .option .tag{font-size:12.5px;color:var(--myhome-primary-ink)}.dialog .option .meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:2px}.dialog .foot{display:flex;justify-content:flex-end;margin-top:12px}.dialog .foot button{min-height:44px;padding:0 16px;border:none;background:transparent;color:var(--myhome-text-soft);font:inherit;font-size:14px;cursor:pointer}`,Sn=(n,t)=>t.missing||t.values.opening_time===void 0?n.t("panel.overview.group.values_unknown"):n.t("panel.dialog.option.profile_meta",{travel:t.reference_height===null?"?":n.number(t.reference_height,0),opening:n.number(t.values.opening_time,1),closing:n.number(t.values.closing_time,1)}),Ai=n=>{let{i18n:t}=n,e=(i,r,o)=>a`<button
    class="option ${n.current===i?"current":""}"
    type="button"
    aria-current=${n.current===i?"true":l}
    @click=${()=>n.onPick(i)}
  >
    <span class="line"
      ><span class="title">${r}</span
      >${n.current===i?a`<span class="tag">${t.t("panel.dialog.option.current")}</span>`:l}</span
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
      <h2 id="dialog-title">${t.t("panel.dialog.title")}</h2>
      <p class="subtitle">
        ${t.t("panel.dialog.subtitle",{cover:n.cover.name})}
      </p>
      <div class="options">
        ${n.profiles.map(i=>e(i.name,t.t("panel.dialog.option.profile",{profile:i.name}),Sn(t,i)))}
        ${e(null,t.t("panel.dialog.option.none"),t.t("panel.dialog.option.none_meta"))}
      </div>
      <div class="foot">
        <button type="button" @click=${n.onClose}>
          ${t.t("panel.common.action.cancel")}
        </button>
      </div>
    </div>
  `};var Ii=m`.groups{display:flex;flex-direction:column;gap:16px}@media(min-width:600px){.groups{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(260px,1fr);gap:16px;align-items:start;overflow-x:auto;padding:4px 0 8px;scroll-padding-inline:4px;scrollbar-width:thin;scrollbar-color:var(--myhome-field-border) transparent;overscroll-behavior-x:contain}.groups::-webkit-scrollbar{height:8px}.groups::-webkit-scrollbar-thumb{background:var(--myhome-field-border);border-radius:4px}.groups::-webkit-scrollbar-track{background:transparent}}.group{position:relative;background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow)}.group-head{padding:16px 16px 12px;border-bottom:1px solid var(--myhome-divider)}.group-head .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.group-head h2{margin:0;font-size:19px;font-weight:700;flex:1 1 auto;min-width:0}.group-head h2 button{border:none;background:transparent;color:var(--myhome-primary);font:inherit;cursor:pointer;padding:0;min-height:28px;text-align:left}.group-head .count{color:var(--myhome-text-soft);font-size:13px}.group-head .meta{margin:6px 0 0;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}.group-head .meta.second{margin-top:4px}.group-head .meta.warn{color:var(--myhome-warning-ink)}.group-body{display:flex;flex-direction:column;padding:8px;gap:2px;min-height:56px}.group-body .empty{margin:8px;font-size:13px;color:var(--myhome-text-soft)}.group-body .insert-end{margin:0 8px;height:3px;border-radius:2px;background:var(--myhome-primary-ink);pointer-events:none}.group .over,.group .armed-target{position:absolute;inset:0;border-radius:var(--myhome-radius);pointer-events:none}.group .over{border:2px solid var(--myhome-primary-ink)}.group .armed-target{border:2px dashed var(--myhome-primary-ink)}.group.collapsed .group-head{border-bottom:none;min-height:48px;cursor:pointer}`,ut=n=>n===null?"none":`profile:${n}`,Mi=n=>n==="none"?null:n.slice(8),Li=(n,t)=>{let{i18n:e}=t,i=n.covers.length===1?e.t("panel.overview.group.count_one"):e.t("panel.overview.group.count",{count:n.covers.length}),r=t.collapsed;return a`<section
    class="group ${r?"collapsed":""}"
    data-group=${ut(n.key)}
    aria-labelledby=${n.id}
  >
    <div
      class="group-head"
      @click=${()=>{r&&t.onTarget(n.key)}}
    >
      <div class="line">
        <h2 id=${n.id}>
          ${n.key===null?n.title:a`<button
                type="button"
                title=${r?e.t("panel.assign.armed",{cover:""}):e.t("panel.overview.group.open")}
                @click=${o=>{if(o.stopPropagation(),r){t.onTarget(n.key);return}t.onOpenProfile(n.key)}}
              >
                ${n.title}
              </button>`}
        </h2>
        <span class="count">${i}</span>
      </div>
      ${n.values&&!r?a`<p class="meta">${n.values}</p>`:l}
      ${r?l:n.warning?a`<p class="meta second warn">${n.warning}</p>`:n.provenance?a`<p class="meta second">${n.provenance}</p>`:l}
    </div>
    ${r?l:a`<div class="group-body">
          ${n.covers.map((o,s)=>Ti(o,{i18n:e,short:o.profile===n.key,first:s===0,pending:t.pending.find(p=>p.cover===o.unique_id),route:t.route(o),locked:t.locked,insertBefore:t.insertBefore===o.unique_id,dragging:t.dragging===o.unique_id,onOpen:t.onOpenCover,onGrab:t.onGrab,onRowPress:t.onRowPress,onPick:t.onPick,onWithdraw:t.onWithdraw}))}
          ${t.insertEnd?a`<div class="insert-end" aria-hidden="true"></div>`:l}
          ${n.covers.length===0?a`<p class="empty">${e.t("panel.overview.group.empty")}</p>`:l}
        </div>`}
    ${t.over?a`<div class="over" aria-hidden="true"></div>`:l}
    ${r?a`<div class="armed-target" aria-hidden="true"></div>`:l}
  </section>`};var Di=[Te,m`.sheet .body[aria-busy=true] table,.sheet .body[aria-busy=true] .note{opacity:.55;transition:opacity .12s ease}.sheet .intro{margin:0 0 16px;font-size:13.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .travel-note{background:var(--myhome-info-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}.sheet .travel-note strong{font-weight:500;display:block;margin-bottom:4px}.sheet .item{border:1px solid var(--myhome-divider);border-radius:8px;padding:12px;margin:0 0 12px}.sheet .item .line{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}.sheet .item .name{font-weight:500;flex:1 1 auto;min-width:0}.sheet .item .item-route{font-size:13px;color:var(--myhome-text-soft)}.sheet label.travel{display:flex;align-items:center;gap:8px;margin:10px 0 2px;font-size:13.5px}.sheet label.travel .what{flex:1}.sheet label.travel input{width:96px;height:44px;border-radius:8px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:inherit;padding:0 10px;font:inherit;font-size:14px;text-align:right}.sheet label.travel input[aria-invalid=true]{border-color:var(--myhome-error-ink)}.sheet .field-error{margin:2px 0 0;font-size:12.5px;color:var(--myhome-error-ink);text-align:right}.sheet table{width:100%;border-collapse:collapse;margin:10px 0 0;font-size:13.5px}.sheet th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}.sheet th.what{text-align:left}.sheet th.after{font-weight:500;color:var(--myhome-text)}.sheet td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}.sheet td.what{text-align:left;color:var(--myhome-text-soft)}.sheet td.after{font-weight:500}.sheet .note{margin:10px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.sheet .problem{margin:10px 0 0;font-size:12.5px;color:var(--myhome-error-ink);line-height:1.5}.sheet .show-all{border:none;background:transparent;color:var(--myhome-primary-ink);font:inherit;font-size:13.5px;cursor:pointer;padding:4px 0;min-height:44px}.sheet .refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 12px;font-size:13.5px;line-height:1.5}.sheet .foot{padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));border-top:1px solid var(--myhome-divider);display:flex;gap:12px;justify-content:flex-end}.sheet .foot button{min-height:44px;border:none;font:inherit;font-size:14px;cursor:pointer}.sheet .foot .back{padding:0 16px;background:transparent;color:var(--myhome-text-soft)}.sheet .foot .confirm{padding:0 24px;border-radius:22px;background:var(--myhome-primary);color:var(--myhome-text-on-primary);font-weight:500}.sheet .foot .confirm[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}`],Rn=(n,t,e,i,r)=>{if(M.every(s=>t.has_own.includes(s)))return n.t("panel.review.note.all_own");if(t.has_own.length>0)return n.t("panel.review.note.some_own");if(e.to===null)return i?.origin==="from_the_file"?n.t("panel.review.note.back_to_file"):n.t("panel.review.note.back_to_defaults");let o=r.get(e.to);return!i||i.height===null||!o||o.reference_height===null?"":n.t("panel.review.note.scaled",{profile:e.to,reference:n.number(o.reference_height,0),travel:n.number(i.height,0)})},Oi=(n,t,e,i)=>n.refusal(e,{cover:t.name,covers:t.name,count:1,profile:i.to??"",key:n.t("panel.review.travel.label"),min:20,max:500}),zi=n=>{let{i18n:t}=n,e=new Map((n.preview??[]).map(d=>[d.cover_unique_id,d])),i=n.pending.map(d=>({change:d,cover:n.covers.get(d.cover)})).filter(d=>d.cover!==void 0),r=i.filter(({change:d,cover:c})=>d.to!==null&&c.height===null&&le(n.heights[d.cover])!==null).length,o=n.showAll?[...pe,...de]:pe,s=d=>z(t.t(`options.step.calibration_edit.data.${d}`)),p=(d,c)=>{let u=X[d];return W(t.number(c,L[d]??1),u?t.t(u):"")};return a`
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
        <h2 id="review-title">${t.t("panel.review.title")}</h2>
        <button
          type="button"
          aria-label=${t.t("panel.common.action.close")}
          ?disabled=${n.applying}
          @click=${n.onClose}
        >
          ✕
        </button>
      </div>
      <div class="body" aria-busy=${n.previewing?"true":"false"}>
        <p class="intro">${t.t("panel.review.intro")}</p>
        ${n.refusal?a`<div class="refusal" role="alert">${n.refusal}</div>`:l}
        ${r>0?a`<div class="travel-note">
              <strong>${t.t("panel.review.travel.title")}</strong>
              ${t.t("panel.review.travel.hint")}
            </div>`:l}
        ${i.map(({change:d,cover:c})=>{let u=e.get(d.cover),h=n.heights[d.cover],g=d.to!==null&&c.height===null,_=g?le(h):null,F=_!==null&&(n.forced||(h??"")!==""),ft=u&&u.problem===null?o.filter(w=>u.values[w]!==void 0&&c.values[w]!==void 0):[];return a`<section class="item">
            <div class="line">
              <span class="name">${c.name}</span>
              <span class="item-route">${n.route(c)}</span>
            </div>
            ${g?a`<label class="travel">
                    <span class="what">${t.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${h??""}
                      ?disabled=${n.applying}
                      aria-label=${t.t("panel.review.travel.aria")}
                      aria-invalid=${F?"true":"false"}
                      placeholder=${t.t("panel.review.travel.placeholder")}
                      @input=${w=>n.onHeight(d.cover,w.target.value)}
                    />
                    <span>${t.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${F?a`<p class="field-error">
                        ${_==="missing_travel"?t.t("panel.review.travel.required"):Oi(t,c,_,d)}
                      </p>`:l}`:l}
            ${u&&u.problem!==null&&u.problem!=="missing_travel"?a`<p class="problem">
                  ${Oi(t,c,u.problem,d)}
                </p>`:l}
            ${ft.length>0?a`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${t.t("panel.review.before")}</th>
                      <th class="after">${t.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${ft.map(w=>a`<tr>
                        <td class="what">${s(w)}</td>
                        <td>${p(w,c.values[w])}</td>
                        <td class="after">${p(w,u.values[w])}</td>
                      </tr>`)}
                  </tbody>
                </table>`:l}
            ${(()=>{let w=Rn(t,c,d,u,n.profiles);return w?a`<p class="note">${w}</p>`:l})()}
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
          ?disabled=${n.applying||n.forced&&r>0}
          @click=${n.onConfirm}
        >
          ${n.applying?t.t("panel.banner.applying.title"):r>0?r===1?t.t("panel.review.action.missing_travel_one"):t.t("panel.review.action.missing_travel",{count:r}):i.length===1?t.t("panel.review.action.confirm_one"):t.t("panel.review.action.confirm",{count:i.length})}
        </button>
      </div>
    </div>
  `};var Ne=class extends f{constructor(){super();this._trap=new Z;this._returnTo=null;this._returnToRow=null;this._onKey=e=>{if(e.key==="Escape"){if(this.state.drag){this._drag.cancel();return}if(this.state.armed){this.actions.arm(null);return}if(this.state.dialog){this.actions.dialog(null);return}this.state.review&&!this.state.applying&&this.actions.review(!1)}};this._flip=null;this._narrowQuery=typeof matchMedia=="function"?matchMedia("(max-width: 599px)"):null;this._onWidth=()=>this.requestUpdate();this._route=e=>{let i=$e(e.unique_id,this.state.pending);return i?ii(this.i18n,e.profile??null,i.to):""};this._onGrab=(e,i)=>{this._drag.press(e.unique_id,i)};this._onRowPress=(e,i)=>{this._narrow&&!this._locked&&this._drag.arm(e.unique_id,i)};this.i18n=new y,this.state=K({view:"overview",params:{},path:"/"}),this.actions={},this._drag=new ze({root:()=>this.renderRoot,blocked:()=>this._locked,narrow:()=>this._narrow,onArm:e=>{let i=this._cover(e);i&&this.actions.arm(i)},onStart:e=>{let i=this._cover(e);i&&(this._drag.ghost(i.name,this.renderRoot),this.actions.drag(i))},onOver:e=>this.actions.over(e),onEnd:e=>this._endDrag(e)})}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[S,R,E,H,He,Pi,Ii,Le,Ci,Di,m`:host{display:block;background:transparent}.intro{margin:8px 0 4px;max-width:72ch}.intro p{margin:0 0 8px;line-height:1.55}.counts{margin:0 0 16px;color:var(--myhome-text-soft)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.controls .search{flex:1 1 220px;max-width:340px}.controls .spacer{flex:1 1 auto}.select-wrap{position:relative;display:inline-flex}.select-wrap:after{content:"";position:absolute;right:13px;top:50%;width:7px;height:7px;border-right:1.6px solid var(--myhome-text-soft);border-bottom:1.6px solid var(--myhome-text-soft);border-radius:1px;transform:translateY(-70%) rotate(45deg);pointer-events:none}select.field{appearance:none;padding-right:36px}a.cta{display:inline-flex;align-items:center;text-decoration:none}.welcome{max-width:640px;margin:48px auto;padding:32px}.welcome h2{margin:0 0 12px;font-size:22px;font-weight:500}.welcome p{margin:0 0 8px;line-height:1.55}.welcome .soft{color:var(--myhome-text-soft);margin-bottom:24px}.welcome .after{margin:12px 0 0;font-size:13px;color:var(--myhome-text-soft)}.notice{padding:16px;margin:16px 0;font-size:14px;line-height:1.55}.notice .actions{margin-top:12px}.groups{margin-bottom:96px}.groups.targeting{margin-bottom:120px}.drag-ghost{position:fixed;left:0;top:0;z-index:80;pointer-events:none;background:var(--myhome-card);color:var(--myhome-text);border:1px solid var(--myhome-primary-ink);border-radius:8px;box-shadow:var(--myhome-shadow);padding:10px 14px;font-size:14px;max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}`]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey),this._narrowQuery?.addEventListener("change",this._onWidth)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey),this._narrowQuery?.removeEventListener("change",this._onWidth),this._drag.stop(),this._trap.release()}updated(e){if(this._locked){let i=this._drag.dragging!==null;this._drag.stop(),i&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"))}if(e.has("state")){let i=e.get("state");if(this._manageFocus(i),this._flip){let r=this._flip;this._flip=null,requestAnimationFrame(()=>Ei(this.renderRoot,r))}}}_beforeMove(){this._flip=Ri(this.renderRoot)}_manageFocus(e){let i=this.state.dialog!==null||this.state.review,r=(e?.dialog??null)!==null||(e?.review??!1);if(i&&!r){let o=this._activeElement();this._returnTo=o,this._returnToRow=o?.closest("[data-row]")?.getAttribute("data-row")??null,requestAnimationFrame(()=>{let s=this.renderRoot.querySelector("[data-focus-root]");s&&this._trap.hold(s)});return}if(!i&&r){this._trap.release();let o=this._returnTo,s=this._returnToRow;this._returnTo=null,this._returnToRow=null,requestAnimationFrame(()=>{((s?[...this.renderRoot.querySelectorAll("[data-row]")].find(c=>c.getAttribute("data-row")===s)?.querySelector(".handle"):null)??(o?.isConnected?o:null))?.focus()})}}_activeElement(){let e=this.renderRoot.activeElement;return e instanceof HTMLElement?e:null}get _overview(){return this.state.overview}get _locked(){return this._overview?.measuring!=null||this.state.applying}get _narrow(){return this._narrowQuery?.matches??!1}_cover(e){return this._overview?.covers.find(i=>i.unique_id===e)}get _covers(){let e=this._overview;return e?ri(e,this.state.order):[]}get _rooms(){let e=new Set;for(let i of this._overview?.covers??[])i.area&&e.add(i.area);return Array.from(e).sort((i,r)=>i.localeCompare(r,this.i18n.language))}_matches(e){let i=this.state.search.trim().toLowerCase();return i&&!e.name.toLowerCase().includes(i)?!1:!this.state.room||e.area===this.state.room}_valuesLine(e){return e.missing||!e.values||e.values.opening_time===void 0?this.i18n.t("panel.overview.group.values_unknown"):this.i18n.t("panel.overview.group.values",{travel:e.reference_height===null?"?":this.i18n.number(e.reference_height,0),opening:this.i18n.number(e.values.opening_time,1),closing:this.i18n.number(e.values.closing_time,1),slat:this.i18n.number(e.values.slat_time,1)})}_provenanceLine(e){if(e.source==="yaml"||(this._overview?.covers??[]).some(p=>p.profile===e.name&&p.profile_from_file))return this.i18n.t("panel.overview.group.from_file");if(!e.measured_on)return this.i18n.t("panel.overview.group.provenance_missing");let r=e.measured_at?this.i18n.date(e.measured_at):"";if(!e.measured_on_name)return this.i18n.t("panel.overview.group.measured_on_gone",{date:r});let o=this.i18n.t("panel.overview.group.measured_on",{cover:e.measured_on_name,date:r}),s=(this._overview?.covers??[]).find(p=>p.unique_id===e.measured_on);if(s&&s.profile!==e.name){let p=s.profile??this.i18n.t("panel.overview.group.no_profile");o+=` · ${this.i18n.t("panel.profile.provenance_now_profile",{profile:p})}`}return o}get _groups(){let e=this._overview;if(!e)return[];let i=this._covers,r=s=>i.filter(p=>xe(p,this.state.pending)===s&&this._matches(p)),o=e.profiles.map((s,p)=>({key:s.name,id:`group-${p}`,title:this.i18n.t("panel.overview.group.profile",{profile:s.name}),values:this._valuesLine(s),provenance:this._provenanceLine(s),warning:s.missing?this.i18n.t("panel.overview.group.missing"):"",covers:r(s.name)}));return o.push({key:null,id:"group-none",title:this.i18n.t("panel.overview.group.no_profile"),values:this.i18n.t("panel.overview.group.no_profile_note"),provenance:"",warning:"",covers:r(null)}),o}_appendAtEnd(e,i){if(this.state.order===null||i===(e.profile??null))return;let r=this._covers;this.actions.setOrder(oi(r.map(o=>o.unique_id),e.unique_id,r.filter(o=>xe(o,this.state.pending)===i).map(o=>o.unique_id)))}_endDrag(e){let i=this.state,r=i.drag,o=r?.insert??null,s=r?.over??null,p=r?this._cover(r.cover):void 0;if(this.actions.drag(null),!e||!p||s===null){r&&this.actions.announce(this.i18n.t("panel.assign.announce.drag_cancelled"));return}let d=Mi(s),c=this._covers.map(_=>_.unique_id),u=lt(c,p.unique_id,o??{beforeId:null,afterId:null});this._beforeMove();let h=$e(p.unique_id,i.pending),g=h?h.to:p.profile??null;if(d!==g){this.actions.setOrder(u),this.actions.assign(p,d);return}if(i.pending.length>0){this.actions.setOrder(u),this.actions.announce(this.i18n.t("panel.assign.announce.reordered"));return}this.actions.reorder(u)}_renderControls(){return a`<div class="controls">
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
      <a class="cta secondary compact" href=${k} title=${this.i18n.t("panel.firstrun.note")}
        >${this.i18n.t("panel.firstrun.action.measure")}</a
      >
    </div>`}_renderFirstRun(){return a`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <a class="cta" href=${k}>${this.i18n.t("panel.firstrun.action.measure")}</a>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`}_renderStrips(){let e=this.state;if(e.route.view!=="overview")return l;if(e.drag)return $i(this.i18n,e.drag.over==="none");if(e.armed){let i=this._cover(e.armed);return ki(this.i18n,i?.name??"",()=>this.actions.arm(null))}return e.applying?Oe(this.i18n):e.snack?De(this.i18n,e.snack.message,e.snack.undoToken?()=>this.actions.undo():null):e.pending.length>0&&!e.review?Si({i18n:this.i18n,count:e.pending.length,locked:this._locked,lockedCover:this._overview?.measuring?.name??"",onDiscard:()=>{this._beforeMove(),this.actions.discardAll()},onReview:()=>this.actions.review(!0)}):l}_renderDialog(){let e=this.state.dialog?this._cover(this.state.dialog):void 0;return e?Ai({i18n:this.i18n,cover:e,profiles:this._overview?.profiles??[],current:xe(e,this.state.pending),onPick:i=>{this._beforeMove(),this._appendAtEnd(e,i),this.actions.assign(e,i)},onClose:()=>this.actions.dialog(null)}):l}_renderReview(){let e=this._overview;return!this.state.review||!e?l:zi({i18n:this.i18n,pending:this.state.pending,covers:new Map(e.covers.map(i=>[i.unique_id,i])),profiles:new Map(e.profiles.map(i=>[i.name,i])),preview:this.state.preview,previewing:this.state.previewing,heights:this.state.heights,forced:this.state.heightsForced,showAll:this.state.showAll,applying:this.state.applying,refusal:this.state.writeError?this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{}):"",route:this._route,onHeight:(i,r)=>this.actions.height(i,r),onToggleShowAll:()=>this.actions.toggleShowAll(),onConfirm:()=>this.actions.confirm(),onClose:()=>this.actions.review(!1)})}render(){let e=this._overview;if(!e)return a`<p>${this.i18n.t("panel.common.loading")}</p>`;if(e.no_basic_covers)return a`<section class="card welcome">
        <h2>${this.i18n.t("panel.overview.no_basic_covers_title")}</h2>
        <div>${Y(this.i18n.t("panel.overview.no_basic_covers"))}</div>
        <a class="cta secondary" href=${k} title=${this.i18n.t("panel.common.opens_configure")}
          >${this.i18n.t("panel.common.action.configure")}</a
        >
      </section>`;if(e.profiles.length===0)return this._renderFirstRun();let i=this._groups,r=i.reduce((p,d)=>p+d.covers.length,0),o=this.state.search.trim()!==""||this.state.room!=="",s=this.state.drag;return a`
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
            ${i.map(p=>{let d=ut(p.key),c=s?.insert??null,u=c!==null&&c.group===d;return Li(p,{i18n:this.i18n,pending:this.state.pending,route:this._route,locked:this._locked,collapsed:this.state.armed!==null,over:s?.over===d,insertBefore:u?c.beforeId:null,insertEnd:u?c.end||c.afterId===p.covers.at(-1)?.unique_id:!1,dragging:s?.cover??null,onOpenProfile:h=>this.actions.openProfile(h),onOpenCover:h=>this.actions.openCover(h.unique_id),onGrab:this._onGrab,onRowPress:this._onRowPress,onPick:h=>this.actions.dialog(h),onWithdraw:h=>{this._beforeMove(),this.actions.withdraw(h)},onTarget:h=>{let g=this.state.armed?this._cover(this.state.armed):void 0;g&&(this._beforeMove(),this._appendAtEnd(g,h),this.actions.assign(g,h))}})})}
          </div>`}
      ${this._renderStrips()} ${this._renderDialog()} ${this._renderReview()}
    `}};customElements.get("myhome-overview")||customElements.define("myhome-overview",Ne);var qe=m`:host{display:block}.card{padding:16px;margin:0 0 16px;max-width:720px}h2{margin:0 0 4px;font-size:16px;font-weight:500}h2:focus-visible{outline:2px solid var(--myhome-primary-ink);outline-offset:4px}.sub{margin:0;font-size:13px;color:var(--myhome-text-soft)}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}.intro{margin:0 0 12px;font-size:13px;color:var(--myhome-text-soft);line-height:1.5}table[aria-busy=true],.rows[aria-busy=true]{opacity:.55;transition:opacity .12s ease}.rows{display:flex;flex-direction:column}.row{display:flex;align-items:baseline;gap:8px;padding:8px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.row .what{flex:1 1 150px;color:var(--myhome-text-soft)}.row .value{font-variant-numeric:tabular-nums;font-weight:500}.row .from{flex-basis:100%;font-size:12px;color:var(--myhome-text-soft);text-align:right}.row .instead{font-size:12px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}h3{margin:16px 0 4px;font-size:14px;font-weight:500}.actions{display:flex;flex-direction:column;gap:8px}.wide{min-height:48px;border:none;border-radius:8px;background:var(--myhome-primary-faint);color:var(--myhome-primary-ink);font:inherit;font-size:14px;cursor:pointer;text-align:left;padding:10px 14px;display:block;width:100%}.wide.destructive{background:var(--myhome-error-strong);color:var(--myhome-error-ink)}.wide[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default}.wide .note{display:block;color:var(--myhome-text-soft);font-size:12.5px;margin-top:2px}.warn{background:var(--myhome-warning-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13px;line-height:1.5}.warn strong{font-weight:500;display:block;margin-bottom:4px}.caution{background:var(--myhome-warning-pastel);border-left:4px solid var(--myhome-warning-ink);border-radius:0 8px 8px 0;padding:12px 12px 12px 14px;margin:8px 0 2px;font-size:13px;line-height:1.5}.caution strong{display:block;font-size:14px;font-weight:700;margin-bottom:4px}.caution p{margin:0}.danger{background:var(--myhome-error-pastel);border-radius:8px;padding:16px;font-size:14px;line-height:1.55}.danger strong{font-weight:500}.danger p{margin:8px 0 0}.danger ul{margin:4px 0 0;padding:0 0 0 20px;line-height:1.7}.danger .soft{color:var(--myhome-text-soft);font-size:13px}.fields{display:flex;flex-direction:column;gap:10px}label.field-row{display:flex;align-items:center;gap:8px;font-size:13.5px}label.field-row .what{flex:1}label.field-row input{width:110px;text-align:right}label.field-row .unit{color:var(--myhome-text-soft);width:24px}.field[aria-invalid=true]{border-color:var(--myhome-error-ink)}.field-error{margin:2px 26px 0 0;font-size:12.5px;color:var(--myhome-error-ink);text-align:right}.foot{display:flex;gap:12px;justify-content:flex-end;margin-top:16px}table{width:100%;border-collapse:collapse;margin:16px 0 0;font-size:13.5px}th{font-weight:400;color:var(--myhome-text-soft);padding:4px 0;border-bottom:1px solid var(--myhome-divider);text-align:right}th.what,td.what{text-align:left}th.after{font-weight:500;color:var(--myhome-text)}td{padding:5px 0;text-align:right;font-variant-numeric:tabular-nums}td.what{color:var(--myhome-text-soft)}td.after{font-weight:500}a{color:var(--myhome-primary-ink)}.refusal{background:var(--myhome-error-pastel);border-radius:8px;padding:12px;margin:0 0 16px;font-size:13.5px;line-height:1.5}`,me=(n,t,e,i,r)=>a`<div class="row">
  <span class="what">${n}</span>
  <span class="value">${t}${e?a` ${e}`:l}</span>
  ${r?a`<span class="instead">${r}</span>`:l}
  ${i?a`<span class="from">${i}</span>`:l}
</div>`,Ue=(n,t)=>a`<div
  class="caution"
  role="note"
  aria-labelledby="advanced-note-title"
  data-advanced-note
>
  <strong id="advanced-note-title">${n}</strong>
  <p>${t}</p>
</div>`,We=(n,t,e,i,r)=>{let o=n.find(s=>e.includes(t(s)));return n.map(s=>s===o?a`${i()}${r(s)}`:r(s))},ue=n=>a`<div>
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
      @input=${t=>n.onInput(t.target.value)}
    />
    <span class="unit">${n.unit}</span>
  </label>
  ${n.error?a`<p class="field-error">${n.error}</p>`:l}
</div>`,x=n=>a`<button
  class="wide ${n.destructive?"destructive":""}"
  type="button"
  title=${n.title??""}
  ?disabled=${n.disabled??!1}
  @click=${n.onClick}
>
  ${n.label}
  ${n.note?a`<span class="note">${n.note}</span>`:l}
</button>`,P=(n,t,e,i=!1)=>a`<div class="foot">
  <button class="cta text" type="button" ?disabled=${i} @click=${t}>
    ${n}
  </button>
  ${e}
</div>`;var Q=[...pe,...de],Be=class extends f{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)&&this.state.dialog===null){if(this.state.detail.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new y,this.state=K({view:"cover",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[S,R,E,H,He,qe,Ie]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.detail,i=`${e.for??""}|${e.mode}`;if(i===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=i,G(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}_fullLabel(e){return this.i18n.t(`options.step.calibration_edit.data.${e}`)}_label(e){return z(this._fullLabel(e))}_unit(e){let i=X[e];return i?this.i18n.t(i):""}_number(e,i){return this.i18n.number(i,L[e]??O[e]?.decimals??1)}_problem(e,i){return this.i18n.refusal(i,{key:this._fullLabel(e),min:O[e]?.min??0,max:O[e]?.max??0,cover:this.state.detail.answer?.cover.name??""})}_destination(){let e=this.state.detail.answer?.forget;return e?e.falls_back_to==="profile"?this.i18n.t("panel.detail.destination.profile",{profile:e.profile??""}):e.falls_back_to==="file"?this.i18n.t("panel.detail.destination.file"):this.i18n.t("panel.detail.destination.defaults"):""}render(){let e=this.state.detail;return e.loading?Me(this.i18n):e.answer?a`${this._head(e.answer.cover)}
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
      </div>`}_head(e){let i=[e.area,e.height===null?this.i18n.t("panel.overview.cover.travel_unknown"):this.i18n.t("panel.overview.cover.travel",{travel:this.i18n.number(e.height,0)}),e.profile?this.i18n.t("panel.overview.cover.follows",{profile:e.profile}):null].filter(o=>!!o),r=e.level==="precise"?this.i18n.t("panel.detail.level_thorough"):e.level==="basic"?this.i18n.t("panel.detail.level_basic"):null;return a`<section class="card">
      <p class="sub">${i.join(" · ")}</p>
      <div class="chips">
        ${Fe(this.i18n,e.origin,e.profile,!1)}
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
            ${this.i18n.t("panel.overview.group.from_file")}
          </p>`:l}
    </section>`}_view(e,i){let r=Q.map(p=>i.find(d=>d.key===p)).filter(p=>p!==void 0),o=e.has_own.length>0,s=o&&e.level!=="precise";return a`<section class="card">
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
        ${s?this._flowButton("panel.detail.action.thorough","panel.detail.action.thorough_note"):l}
        ${o?x({label:this.i18n.t("panel.detail.action.remove"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("remove")}):l}
      </section>`}_valueRow(e,i){let r=i.origin==="own"?this.i18n.t("panel.detail.source.own"):i.origin==="profile"?this.i18n.t("panel.detail.source.profile",{profile:e.profile??""}):i.origin==="file"?this.i18n.t("panel.detail.source.file"):this.i18n.t("panel.detail.source.default");return me(this._label(i.key),this._number(i.key,i.value),this._unit(i.key),r,i.own&&i.inherited_value!==null?this.i18n.t("panel.detail.edit.inherits",{value:this._number(i.key,i.inherited_value)}):null)}_flowButton(e,i){return x({label:`${this.i18n.t(e)} ↗`,note:this.i18n.t(i),title:this.i18n.t("panel.common.opens_configure"),onClick:r=>this.actions.openFlow(r.currentTarget)})}_edit(e){let i=this.state.detail.form,r=Q.map(s=>e.find(p=>p.key===s)).filter(s=>s!==void 0),o=r.some(s=>b(s.key,i[s.key])!==null);return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.edit.title")}</h2>
      <div class="warn">${this.i18n.t("panel.detail.edit.intro")}</div>
      <div class="fields">
        ${We(r,s=>s.key,ke,()=>this._advancedNote(),s=>this._field(s))}
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||o}
          @click=${this.actions.saveValues}>
          ${this.i18n.t("panel.detail.edit.action.save")}
        </button>`,this.state.applying)}
    </section>`}_advancedNote(){return Ue(this.i18n.t("panel.common.advanced.title"),this.i18n.t("panel.common.advanced.body"))}_field(e){let i=this.state.detail.form[e.key],r=b(e.key,i),o=e.inherited_value===null?this.i18n.t("panel.detail.edit.empty"):this.i18n.t("panel.detail.edit.inherits",{value:this._number(e.key,e.inherited_value)});return ue({label:this._label(e.key),value:i??"",unit:this._unit(e.key),placeholder:o,error:r?this._problem(e.key,r):null,disabled:this.state.applying,onInput:s=>this.actions.field(e.key,s)})}_travel(e){let i=this.state.detail.form.height,r=b("height",i),o=this.state.detail.preview,s=o&&o.problem===null?Q.filter(p=>o.values[p]!==void 0&&e.values[p]!==void 0):[];return a`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this._label("height")}
      </h2>
      <p class="intro">
        ${this.i18n.t("options.step.calibration_edit.data_description.height")}
      </p>
      ${ue({label:this.i18n.t("panel.review.travel.label"),ariaLabel:this.i18n.t("panel.review.travel.aria"),value:i??"",unit:this.i18n.t("panel.common.unit.centimetres"),placeholder:this.i18n.t("panel.review.travel.placeholder"),error:r?this._problem("height",r):null,disabled:this.state.applying,onInput:p=>this.actions.field("height",p)})}
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
                  <td>${W(this._number(p,e.values[p]),this._unit(p))}</td>
                  <td class="after">
                    ${W(this._number(p,o.values[p]),this._unit(p))}
                  </td>
                </tr>`)}
            </tbody>
          </table>`:l}
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||r!==null||$(i)}
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
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.detail.remove.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-cover-detail")||customElements.define("myhome-cover-detail",Be);var J=["reference_height",...M],Hi=64,En=new RegExp(`^[A-Za-z0-9_]{1,${Hi}}$`),Ke=class extends f{constructor(){super();this._onKey=e=>{if(!(e.key!=="Escape"||this.state.applying)&&this.state.dialog===null){if(this.state.profile.mode!=="view"){this.actions.mode("view");return}this.actions.back()}};this._focused="";this.i18n=new y,this.state=K({view:"profile",params:{},path:"/"}),this.actions={}}static{this.properties={i18n:{attribute:!1},state:{attribute:!1},actions:{attribute:!1}}}static{this.styles=[S,R,E,H,qe]}connectedCallback(){super.connectedCallback(),window.addEventListener("keydown",this._onKey)}disconnectedCallback(){super.disconnectedCallback(),window.removeEventListener("keydown",this._onKey)}updated(){let e=this.state.profile,i=`${e.for??""}|${e.mode}`;if(i===this._focused)return;let r=this.renderRoot.querySelector("[data-heading]");r&&(this._focused=i,G(()=>r))}get _locked(){return this.state.overview?.measuring!=null||this.state.applying}get _profile(){let e=this.state.profile.for;return this.state.overview?.profiles.find(i=>i.name===e)??null}get _followers(){let e=this._profile,i=this.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return i.filter(o=>r.has(o.unique_id))}_fullLabel(e){return e==="reference_height"?this.i18n.t("panel.profile.reference_travel"):this.i18n.t(`options.step.profile_edit.data.${e}`)}_label(e){return z(this._fullLabel(e))}_unit(e){let i=X[e];return i?this.i18n.t(i):""}_number(e,i){return this.i18n.number(i,L[e]??O[e]?.decimals??1)}_problem(e,i){return this.i18n.refusal(i,{key:this._fullLabel(e),min:O[e]?.min??0,max:O[e]?.max??0})}_ownKeys(e){return e.has_own.map(i=>z(this.i18n.t(`options.step.calibration_edit.data.${i}`))).join(", ")}render(){let e=this._profile;if(!this.state.overview)return a`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;if(!e)return a`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.unknown")}</h2>
        ${P(this.i18n.t("panel.common.action.back"),this.actions.back,l)}
      </div>`;let i=this.state.profile.mode;return a`${this._head(e)}
    ${this.state.writeError?a`<div class="card refusal" role="alert">
          ${this.i18n.refusal(this.state.writeError.translation_key,this.state.writeError.translation_placeholders??{})}
        </div>`:l}
    ${i==="view"?this._view(e):l}
    ${i==="edit"?this._edit():l}
    ${i==="rename"?this._rename(e):l}
    ${i==="delete"?this._delete(e):l}`}_head(e){let r=(this.state.overview?.covers??[]).find(p=>p.unique_id===e.measured_on),o;e.measured_on&&e.measured_on_name&&e.measured_at?(o=this.i18n.t("panel.profile.provenance",{cover:e.measured_on_name,date:this.i18n.date(e.measured_at)}),r&&r.profile!==e.name&&(o+=` · ${r.profile?this.i18n.t("panel.profile.provenance_now_profile",{profile:r.profile}):this.i18n.t("panel.profile.provenance_now_none")}`)):e.measured_on&&e.measured_at?o=this.i18n.t("panel.overview.group.measured_on_gone",{date:this.i18n.date(e.measured_at)}):o=this.i18n.t("panel.profile.provenance_missing");let s=e.editable?this.i18n.t("panel.profile.stored"):this.i18n.t("panel.profile.from_file");return a`<section class="card">
      <p class="sub">${e.missing?o:`${s} · ${o}`}</p>
      ${e.missing?a`<p class="warn" style="margin:12px 0 0">
            ${this.i18n.t("panel.overview.group.values_unknown")}
          </p>`:l}
    </section>`}_view(e){let i=this._followers;return a`${e.missing?l:a`<section class="card">
            <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.values")}</h2>
            <div class="rows">
              ${J.map(r=>r==="reference_height"?e.reference_height===null?l:me(this._label(r),this._number(r,e.reference_height),this._unit(r),"",null):e.values[r]===void 0?l:me(this._label(r),this._number(r,e.values[r]),this._unit(r),"",null))}
            </div>
          </section>`}
      <section class="card">
        <h2 ?data-heading=${e.missing} tabindex="-1">
          ${i.length===0?this.i18n.t("panel.profile.followers.none"):i.length===1?this.i18n.t("panel.profile.followers.count_one"):this.i18n.t("panel.profile.followers.count",{count:i.length})}
        </h2>
        <p class="intro">${this.i18n.t("panel.profile.edit.intro")}</p>
        <div class="rows">
          ${i.map(r=>this._follower(r))}
        </div>
      </section>
      ${e.editable?a`<section class="card actions">
            ${x({label:this.i18n.t("panel.profile.action.edit"),disabled:this._locked,onClick:()=>this.actions.mode("edit")})}
            ${x({label:this.i18n.t("panel.profile.action.rename"),disabled:this._locked,onClick:()=>this.actions.mode("rename")})}
            ${x({label:this.i18n.t("panel.profile.action.delete"),destructive:!0,disabled:this._locked,onClick:()=>this.actions.mode("delete")})}
          </section>`:l}`}_follower(e){let r=M.every(o=>e.has_own.includes(o))?this.i18n.t("panel.profile.followers.measured"):e.has_own.length>0?this.i18n.t("panel.profile.followers.adjusted",{keys:this._ownKeys(e)}):this.i18n.t("panel.profile.followers.inherited");return a`<div class="row">
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
      ${e.profile_from_file?a`<span class="from">${this.i18n.t("panel.detail.source.file")}</span>`:l}
    </div>`}_edit(){let e=this._followers,i=this.state.profile.form,r=J.some(s=>b(s,i[s])!==null||$(i[s])),o=e.length===1?this.i18n.t("panel.profile.edit.reach_one"):this.i18n.t("panel.profile.edit.reach_all",{count:e.length});return a`<section class="card">
      <!-- The button that opens this says "Modifica i valori…": the dots are the button's
           promise of a further step, and the heading is that step. -->
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.edit.title")}</h2>
      <div class="warn">
        <strong>${this.i18n.t("panel.profile.edit.reach",{target:o})}</strong>
        ${this.i18n.t("panel.profile.edit.intro")}
      </div>
      <div class="fields">
        ${We(J,s=>s,ke,()=>Ue(this.i18n.t("panel.common.advanced.title"),this.i18n.t("panel.common.advanced.body")),s=>ue({label:this._label(s),value:i[s]??"",unit:this._unit(s),error:$(i[s])?this.i18n.t("panel.common.required"):(()=>{let p=b(s,i[s]);return p?this._problem(s,p):null})(),disabled:this.state.applying,onInput:p=>this.actions.field(s,p)}))}
      </div>
      <h3>${this.i18n.t("panel.profile.impact.title")}</h3>
      <div class="rows" aria-busy=${this.state.profile.impacting?"true":"false"}>
        ${e.map(s=>this._impact(s,r))}
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button" ?disabled=${this._locked||r}
          @click=${this.actions.saveValues}>
          ${e.length===1?this.i18n.t("panel.profile.edit.action.save_one"):this.i18n.t("panel.profile.edit.action.save",{count:e.length})}
        </button>`,this.state.applying)}
    </section>`}_impact(e,i){let r=M.every(p=>e.has_own.includes(p)),o=r?this.i18n.t("panel.profile.impact.state_measured"):e.has_own.length>0?this.i18n.t("panel.profile.impact.state_adjusted"):this.i18n.t("panel.profile.impact.state_inherited"),s;if(r)s=this.i18n.t("panel.profile.impact.no_change");else if(e.height===null)s=this.i18n.t("panel.profile.impact.no_travel");else if(i)s=this.i18n.t("panel.profile.impact.invalid");else{let p=(this.state.profile.impact??[]).find(d=>d.cover_unique_id===e.unique_id);if(!p||p.problem!==null)s=this.i18n.t("panel.common.loading");else if(s=M.filter(c=>!e.has_own.includes(c)&&e.values[c]!==void 0&&p.values[c]!==void 0).map(c=>`${z(this.i18n.t(`options.step.calibration_edit.data.${c}`))} ${this._number(c,e.values[c])} → `+W(this._number(c,p.values[c]),this._unit(c))).join(" · "),e.has_own.length>0){let c=this.i18n.t("panel.profile.impact.kept",{keys:this._ownKeys(e)});s=s?`${s} — ${c}`:c}}return a`<div class="row">
      <span class="what">${e.name}</span>
      <span class="instead">${o}</span>
      <span class="from" style="text-align:left">${s}</span>
    </div>`}_rename(e){let i=this.state.profile.newName,r=i.trim()!==""&&!En.test(i.trim()),o=r?this.i18n.refusal("invalid_name",{profile:i}):this.state.profile.nameError;return a`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.rename.title")}</h2>
      <p class="intro">${this.i18n.t("panel.profile.rename.rule")}</p>
      <label class="field-row">
        <span class="what">${this.i18n.t("panel.profile.rename.field")}</span>
        <input
          class="field"
          type="text"
          style="width:220px;text-align:left"
          maxlength=${Hi}
          .value=${i}
          ?disabled=${this.state.applying}
          aria-label=${this.i18n.t("panel.profile.rename.field")}
          aria-invalid=${o?"true":"false"}
          @input=${s=>this.actions.newName(s.target.value)}
        />
      </label>
      ${o?a`<p class="field-error" style="text-align:left">${o}</p>`:l}
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact" type="button"
          ?disabled=${this._locked||r||i.trim()===""||i.trim()===e.name}
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
                ${i.map(r=>a`<li>${r.name}</li>`)}
              </ul>`}
        <p>${this.i18n.t("panel.profile.delete.body")}</p>
      </div>
      ${P(this.i18n.t("panel.common.action.cancel"),()=>this.actions.mode("view"),a`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.profile.delete.action")}
        </button>`,this.state.applying)}
    </section>`}};customElements.get("myhome-profile-card")||customElements.define("myhome-profile-card",Ke);var Fi=(n,t)=>n.summary?.note?a`<div class="stub">${n.summary.note}</div>`:l;var Ni=(n,t)=>{let e=n.options??[];return e.length===0?l:a`<div class="options" role="group" aria-label=${n.title}>
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
  </div>`};var qi=(n,t)=>{let e=n.progress;if(!e)return a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let i=Math.max(0,Math.min(1,e.fraction))*100;return a`<div class="progress-card">
    ${e.text?a`<p class="instruction">${e.text}</p>`:l}
    <div
      class="progress-track"
      role="progressbar"
      aria-label=${e.text||t.i18n.t("panel.screen.progress")}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow=${Math.round(i)}
    >
      <div class="progress-bar" style=${`width:${i}%`}></div>
    </div>
    <p class="progress-eta" role="status">
      ${e.done?t.i18n.t("panel.screen.completed"):e.eta??""}
    </p>
  </div>`};var Ui=(n,t)=>{let e=n.press;if(!e)return a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let i=e.state==="moving";return a`
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
  `};var Wi=(n,t)=>{let e=n.options??[];if(e.length===0&&!n.field)return a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`;let i=n.field;return a`
    <div class="options" role="group" aria-label=${n.title}>
      ${e.map(r=>a`<button
          class="option"
          type="button"
          aria-pressed=${r.current?"true":"false"}
          @click=${()=>t.fire(r.action)}
        >
          <strong class="option-title">${r.title}</strong>
          ${r.meta?a`<span class="option-meta">${r.meta}</span>`:l}
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
              @input=${r=>t.fire("field",r.target.value)}
            />
            ${i.unit?a`<span class="unit">${i.unit}</span>`:l}
          </div>
          ${i.error?a`<p class="error" id="gap-error" role="alert">${i.error}</p>`:l}
        </div>`:l}
  `};var Pn=n=>{let t=[n.hint?"reading-hint":"",n.error?"reading-error":""].filter(e=>e!=="");return t.length>0?t.join(" "):void 0},Bi=(n,t)=>{let e=n.field;return e?a`<div class="reading ${e.big===!1?"":"big"}">
    <label for="reading">${e.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${e.value}
        placeholder=${e.placeholder??""}
        aria-describedby=${Pn(e)??l}
        aria-invalid=${e.error?"true":"false"}
        @input=${i=>t.fire("field",i.target.value)}
      />
      ${e.unit?a`<span class="unit">${e.unit}</span>`:l}
    </div>
    ${e.hint?a`<p class="hint" id="reading-hint">${e.hint}</p>`:l}
    ${e.error?a`<p class="error" id="reading-error" role="alert">${e.error}</p>`:l}
  </div>`:a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`};var Ki=(n,t)=>{let e=n.summary;return e?a`
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
  `:a`<div class="stub">${t.i18n.t("panel.screen.not_in_this_version")}</div>`};var Gi=(n,t)=>n.summary?.rows?.length?a`<div class="summary">
    ${n.summary.rows.map(e=>a`<div class="summary-row">
        <span class="label">${e.label}</span>
        <span class="after">${e.after}</span>
      </div>`)}
    ${n.summary.note?a`<p class="note-line">${n.summary.note}</p>`:l}
  </div>`:l;var ji=m`.text-column{min-width:0}.phase{margin:0 0 8px;font-size:12px;color:var(--myhome-text-soft)}.new-text{display:inline-block;margin:0 0 12px;background:var(--myhome-info-pastel);border-radius:10px;padding:3px 10px;font-size:12px;color:var(--myhome-text-soft)}.screen-title{margin:0 0 12px;font-size:20px;font-weight:500;line-height:1.3;display:flex;align-items:center;gap:10px}.outcome-icon{width:32px;height:32px;flex:0 0 32px;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;font-weight:600}.outcome-icon.saved{background:var(--myhome-success-pastel);color:var(--myhome-success-ink)}.outcome-icon.saved:before{content:"\2713"}.outcome-icon.cancelled{background:var(--myhome-error-pastel);color:var(--myhome-error-ink)}.outcome-icon.cancelled:before{content:"\2715"}.outcome-icon.expired{background:var(--myhome-warning-pastel);color:var(--myhome-warning-ink)}.outcome-icon.expired:before{content:"\29d7"}.outcome-icon.problem{background:var(--myhome-error-pastel);color:var(--myhome-error-ink)}.outcome-icon.problem:before{content:"!"}.drawing{height:230px;border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);margin:0 0 16px;background-color:var(--myhome-drawing-paper);background-repeat:no-repeat}.prose p{margin:0 0 12px;font-size:14.5px;line-height:1.6;text-wrap:pretty}.prose ul{margin:0 0 12px;padding-left:20px;font-size:14.5px;line-height:1.6}.prose .md-image{display:block;max-width:100%;border-radius:var(--myhome-radius);margin:0 0 12px}.big{width:100%;min-height:64px;border:none;border-radius:16px;font:inherit;font-size:16px;font-weight:600;cursor:pointer;background:var(--myhome-primary);color:var(--myhome-text-on-primary);box-shadow:var(--myhome-shadow)}.big.moving{background:var(--myhome-accent);color:var(--myhome-text)}.big[disabled]{background:var(--myhome-background-soft);color:var(--myhome-text-off);cursor:default;box-shadow:none}.options{display:flex;flex-direction:column;gap:8px;margin:4px 0 0}.option{text-align:left;border-radius:10px;font:inherit;padding:14px;min-height:56px;cursor:pointer;color:inherit;border:1px solid var(--myhome-field-border);background:var(--myhome-card)}.option[aria-pressed=true]{border-color:var(--myhome-primary-ink);box-shadow:inset 0 0 0 1px var(--myhome-primary);background:var(--myhome-primary-faint)}.option .option-head{display:flex;align-items:center;gap:8px}.option .option-title{font-weight:500;flex:1;font-size:14.5px;line-height:1.4}.option .option-meta{display:block;font-size:12.5px;color:var(--myhome-text-soft);margin-top:3px}.live{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:14px 16px;display:flex;flex-direction:column;gap:8px;font-size:14px}.live-row{display:flex;justify-content:space-between;gap:12px}.live-row .name{color:var(--myhome-text-soft)}.live-row .value{font-variant-numeric:tabular-nums;font-weight:500}.live-row .value.moving{color:var(--myhome-warning-ink);animation:myhome-pulse 1.2s ease-in-out infinite}@keyframes myhome-pulse{0%,to{opacity:1}50%{opacity:.55}}.chip{font-size:12px;border-radius:10px;padding:3px 9px;white-space:nowrap;background:var(--myhome-background-soft);color:var(--myhome-text-soft)}.instruction{margin:0 0 16px;font-size:16.5px;line-height:1.5;font-weight:500}.note{margin:14px 0 0;border-radius:8px;padding:12px 14px;font-size:14px;line-height:1.55}.note.success{background:var(--myhome-success-pastel)}.note.error{background:var(--myhome-error-pastel)}.note.info{background:var(--myhome-info-pastel)}.progress-card{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px}.progress-track{height:8px;border-radius:4px;background:var(--myhome-background-soft);overflow:hidden}.progress-bar{height:100%;background:var(--myhome-primary);border-radius:4px;transition:width .1s linear}.progress-eta{margin:10px 0 0;font-size:13px;color:var(--myhome-text-soft);font-variant-numeric:tabular-nums}.reading{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:16px;margin:4px 0 0}.reading label{display:block;font-size:13.5px;margin:0 0 8px}.reading .row{display:flex;align-items:center;gap:10px}.reading input{flex:1;min-width:0;height:56px;border-radius:10px;border:1px solid var(--myhome-field-border);background:var(--myhome-card);color:inherit;padding:0 14px;font:inherit;font-size:26px;font-variant-numeric:tabular-nums}.reading.big input{height:64px;font-size:32px}.reading .unit{font-size:16px;color:var(--myhome-text-soft)}.reading.big .unit{font-size:18px}.reading .hint{margin:8px 0 0;font-size:12.5px;color:var(--myhome-text-soft);line-height:1.5}.reading .error{margin:8px 0 0;font-size:12.5px;color:var(--myhome-error-ink);line-height:1.5}.summary{background:var(--myhome-card);border-radius:var(--myhome-radius);box-shadow:var(--myhome-shadow);padding:8px 16px;margin:4px 0 14px}.summary-row{display:flex;align-items:baseline;gap:8px;padding:9px 0;border-bottom:1px solid var(--myhome-divider);font-size:13.5px;flex-wrap:wrap}.summary-row:last-of-type{border-bottom:none}.summary-row .label{flex:1 1 130px;color:var(--myhome-text-soft)}.summary-row .before{color:var(--myhome-text-soft);font-variant-numeric:tabular-nums;text-decoration:line-through;opacity:.7}.summary-row .after{font-variant-numeric:tabular-nums;font-weight:500}.summary .note-line{margin:10px 0;font-size:12.5px;color:var(--myhome-text-soft)}.code{background:var(--myhome-background-soft);border-radius:8px;padding:12px 14px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-x:auto}.stub{margin:4px 0 0;background:var(--myhome-info-pastel);border-radius:8px;padding:12px 14px;font-size:13.5px;line-height:1.55}`;var Ge=class extends f{constructor(){super();this._fire=(e,i)=>{this.dispatchEvent(new CustomEvent("myhome-screen-action",{detail:{action:e,value:i,screen:this.model?.id??""},bubbles:!0,composed:!0}))};this.model=null,this.i18n=new y}static{this.properties={model:{attribute:!1},i18n:{attribute:!1}}}static{this.styles=[S,R,E,H,Pe,ji,m`:host{display:block;background:transparent}.screen{width:100%;max-width:480px;margin:0 auto;display:flex;flex-direction:column;position:relative}.pane{flex:1;padding:16px 16px 230px}.right{min-width:0}.footer{position:fixed;bottom:0;left:50%;transform:translate(-50%);width:100%;max-width:480px;padding:36px 16px calc(12px + env(safe-area-inset-bottom,0px));background:linear-gradient(to top,var(--myhome-background) calc(100% - 36px),transparent);z-index:25;display:flex;flex-direction:column;gap:10px}@media(min-width:900px){.screen{max-width:100%}.pane{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:0 44px;align-items:start;width:100%;max-width:1080px;margin:0 auto;padding:24px 32px 48px}.pane.single{display:block;max-width:560px}.right{position:sticky;top:76px}.footer{position:static;transform:none;width:auto;max-width:none;padding:0;background:none;margin-top:20px}}`]}_renderOperative(e,i){switch(e.model){case"scelta":return Ni(e,i);case"pos":return qi(e,i);case"click":return Ui(e,i);case"controllo":return Wi(e,i);case"metro":return Bi(e,i);case"riepilogo":return Ki(e,i);case"esito":return Gi(e,i);case"lettura":return Fi(e,i);default:return l}}_renderFooter(e,i){let r=e.secondary??[];return!e.primary&&r.length===0?l:a`<div class="footer">
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
          @click=${()=>i.fire(o.action)}
        >
          ${o.label}
        </button>`)}
    </div>`}render(){let e=this.model;if(!e)return l;let i={i18n:this.i18n,fire:this._fire},r=e.model==="pos",o=e.image?Ht(e.image):null;return a`<div class="screen">
      <div class="pane ${r?"single":""}">
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
                style=${Ae(o)}
              ></div>`:l}
          ${e.body?a`<div class="prose">${Y(e.body)}</div>`:l}
        </div>
        <div class="right">
          ${this._renderOperative(e,i)} ${this._renderFooter(e,i)}
        </div>
      </div>
    </div>`}};customElements.get("myhome-screen")||customElements.define("myhome-screen",Ge);var Tn=3e4,Cn=7e3,vt=400,An=2e3,gt=class extends f{constructor(){super();this._i18n=new y;this._router=new Se;this._store=new Re(this._router.current);this._unsubscribeStore=null;this._unsubscribeWs=null;this._poll=null;this._language="";this._started=!1;this._snackTimer=null;this._previewTimer=null;this._travelTimer=null;this._impactTimer=null;this._followTimer=null;this._followedAt=0;this._drawerBack=null;this._trap=new Z;this._returnTo=null;this._listening=Promise.resolve();this._subscribing=0;this._previewSeq=0;this._drawerWasOpen=!1;this._dialogWasOpen=!1;this._onSocketDown=()=>{this._store.state.connection!=="offline"&&(this._store.set({connection:"offline"}),this._store.announce(this._i18n.t("panel.error.no_connection")))};this._onSocketReady=()=>{this._afterReconnect()};this._onReturn=()=>{!this._started||document.hidden||this._refresh()};this._closeDrawer=()=>{this._store.state.applying||this._navigate(di(this._drawerBack))};this._assignActions={search:e=>this._store.set({search:e}),room:e=>this._store.set({room:e}),clearFilters:()=>this._store.set({search:"",room:""}),openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:(e,i)=>{if(this._locked)return;let{pending:r,withdrawn:o}=ni(this._store.state.pending,e,i);this._store.set({pending:r,dialog:null,armed:null,writeError:null}),B(this._store.state.route)&&(this._drawerBack=null,this._navigate("/")),this._store.announce(o?this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name}):this._i18n.t("panel.assign.announce.pending",{cover:e.name,target:i===null?this._i18n.t("panel.assign.target_none"):this._i18n.t("panel.assign.target_profile",{profile:i})})),this._schedulePreview()},withdraw:e=>{this._store.set({pending:this._store.state.pending.filter(i=>i.cover!==e.unique_id)}),this._store.announce(this._i18n.t("panel.assign.announce.withdrawn",{cover:e.name})),this._schedulePreview()},discardAll:()=>{this._store.set({...Ee}),this._store.announce(this._i18n.t("panel.assign.announce.discarded"))},reorder:e=>{this._locked||!this._store.state.entryId||(this._store.set({order:e}),this._write(()=>Bt(this.hass.connection,this._store.state.entryId,e),i=>{this._store.set({order:null}),this._store.setOverview(i.overview),this._snack(this._i18n.t("panel.toast.order_saved"),i.undo_token),this._store.announce(this._i18n.t("panel.assign.announce.reordered"))},i=>{this._store.set({order:null,writeError:null}),this._snack(i,null,!1)}))},setOrder:e=>this._store.set({order:e}),drag:e=>this._store.set({drag:e?{cover:e.unique_id,name:e.name,over:null,insert:null}:null}),over:e=>{let i=this._store.state.drag;i&&this._store.set({drag:{...i,over:e?.group??null,insert:e?{...e}:null}})},arm:e=>{this._store.set({armed:e?e.unique_id:null}),e&&this._store.announce(this._i18n.t("panel.assign.announce.armed"))},dialog:e=>this._store.set({dialog:e?e.unique_id:null}),review:e=>{this._store.set({review:e,writeError:null,heightsForced:!1}),e&&this._refreshPreview()},height:(e,i)=>{this._store.set({heights:{...this._store.state.heights,[e]:i}}),this._schedulePreview()},toggleShowAll:()=>this._store.set({showAll:!this._store.state.showAll}),confirm:()=>{this._confirm()},undo:()=>{this._undo()},announce:e=>this._store.announce(e)};this._detailActions={back:this._closeDrawer,retry:()=>{this._store.set({detail:{...this._store.state.detail,loading:!0,error:null}}),this._loadDetail()},openProfile:e=>this._navigate(`/profile/${encodeURIComponent(e)}`),assign:()=>{this._store.set({dialog:this._store.state.detail.for})},mode:e=>{let i=this._store.state.detail,r=this._detailCover,o=e==="edit"?this._detailForm():e==="travel"?{height:r?.height!=null?this._i18n.number(r.height,0):""}:{};this._store.set({detail:{...i,mode:e,form:o,errors:{},preview:null,previewing:!1},writeError:null}),e==="travel"&&this._refreshTravelPreview()},field:(e,i)=>{let r=this._store.state.detail,o=e==="height"&&b("height",i)!==null;o&&(this._previewSeq+=1),this._store.set({detail:{...r,form:{...r.form,[e]:i},...o?{preview:null}:{}}}),e==="height"&&this._scheduleTravelPreview()},saveValues:()=>{this._saveValues()},saveTravel:()=>{this._saveTravel()},remove:()=>{this._removeMeasure()},openFlow:e=>this._openFlow(e)};this._profileActions={back:this._closeDrawer,openCover:e=>this._navigate(`/cover/${encodeURIComponent(e)}`),mode:e=>{let i=this._store.state.profile;this._store.set({profile:{...i,mode:e,form:e==="edit"?this._profileForm(this._profileRow):{},errors:{},newName:e==="rename"?i.for??"":"",nameError:"",impact:null,impacting:!1},writeError:null}),e==="edit"&&this._refreshImpact()},field:(e,i)=>{let r=this._store.state.profile;this._store.set({profile:{...r,form:{...r.form,[e]:i}}}),this._scheduleImpact()},newName:e=>this._store.set({profile:{...this._store.state.profile,newName:e,nameError:""}}),saveValues:()=>{this._saveProfile()},rename:()=>{this._renameProfile()},remove:()=>{this._deleteProfile()}};this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1}}}static{this.styles=[S,R,E,Pe,gi,Ie,Le,ui,m`.toolbar{display:flex;align-items:center;gap:8px;padding:0 8px;background:var(--myhome-header);color:var(--myhome-header-text);font-size:20px;font-weight:400;padding-top:env(safe-area-inset-top,0px);height:calc(56px + env(safe-area-inset-top,0px))}.toolbar .title{flex:1;min-width:0;margin:0;font-size:inherit;font-weight:inherit;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.toolbar select.gateway{font:inherit;font-size:13px;max-width:40%;min-height:44px;border-radius:8px;border:1px solid currentColor;background:transparent;color:inherit;padding:0 6px}.toolbar select.gateway option{color:var(--myhome-text);background:var(--myhome-card)}.toolbar button{width:48px;height:48px;flex:0 0 48px;border:0;border-radius:24px;background:transparent;color:inherit;font-size:20px;line-height:1;cursor:pointer}.content{padding:16px;max-width:1200px;margin:0 auto;padding-bottom:calc(16px + env(safe-area-inset-bottom,0px))}.card.problem{background:var(--myhome-error-pastel);color:var(--myhome-text);padding:16px}.card.waiting{color:var(--myhome-text-soft);padding:16px}.soft{color:var(--myhome-text-soft);font-size:13px;margin-top:8px}.connection{margin:24px 0 0;font-size:12.5px;color:var(--myhome-text-soft)}.offline{display:block;padding:12px 16px;background:var(--myhome-warning-pastel);color:var(--myhome-text);font-size:14px}a{color:var(--myhome-primary-ink)}`]}connectedCallback(){super.connectedCallback(),this._unsubscribeStore=this._store.subscribe(()=>this.requestUpdate()),this._router.start(e=>this._onRoute(e)),window.addEventListener("location-changed",this._onReturn),document.addEventListener("visibilitychange",this._onReturn)}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeStore?.(),this._unsubscribeStore=null,this._router.stop(),this._trap.release(),window.removeEventListener("location-changed",this._onReturn),document.removeEventListener("visibilitychange",this._onReturn),this._unwatchSocket(),this._stopPolling(),this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._previewTimer&&(clearTimeout(this._previewTimer),this._previewTimer=null),this._travelTimer&&(clearTimeout(this._travelTimer),this._travelTimer=null),this._impactTimer&&(clearTimeout(this._impactTimer),this._impactTimer=null),this._followTimer&&(clearTimeout(this._followTimer),this._followTimer=null);let e=this._unsubscribeWs;this._unsubscribeWs=null,e?.().catch(()=>{})}shouldUpdate(e){return e.size>1||!e.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(e){if(this._manageDrawerFocus(),e.has("route")&&(this._router.setHostPath(this.route?.path),this._onRoute(this._router.current)),!(!e.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_manageDrawerFocus(){let e=this._store.state,i=B(e.route)&&e.status!=="error",r=e.dialog!==null,o=()=>this.renderRoot.querySelector("[data-drawer]");if(i&&!this._drawerWasOpen)this._returnTo=ht(this.renderRoot),requestAnimationFrame(()=>{let s=o();s&&this._trap.hold(s,!1)});else if(!i&&this._drawerWasOpen){this._trap.release();let s=this._returnTo;this._returnTo=null,G(()=>s?.isConnected?s:null)}else i&&this._dialogWasOpen&&!r&&requestAnimationFrame(()=>{let s=o();s&&this._trap.hold(s)});this._drawerWasOpen=i,this._dialogWasOpen=r}_languageOf(e){return e?.locale?.language||e?.language||"en"}async _bootstrap(){this._started||!this.hass||(this._started=!0,this._watchSocket(),await this._loadTexts(),await this._refresh(),await this._loadDetail(),await this._listen())}_watchSocket(){let e=this.hass?.connection;e?.addEventListener?.("disconnected",this._onSocketDown),e?.addEventListener?.("ready",this._onSocketReady)}_unwatchSocket(){let e=this.hass?.connection;e?.removeEventListener?.("disconnected",this._onSocketDown),e?.removeEventListener?.("ready",this._onSocketReady)}async _afterReconnect(){this._started&&(this._store.set({connection:this._unsubscribeWs?"live":"polling"}),await this._refresh(),!this._unsubscribeWs&&!this._subscribing&&await this._listen(),this._store.announce(this._i18n.t("panel.common.reconnected")))}async _loadTexts(){let e=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,e)}catch{}this._language=e,this.requestUpdate()}async _refresh(){try{let e=await Ft(this.hass.connection,this._store.state.entryId??void 0);this._store.setOverview(e)}catch(e){this._store.setError(A(e))}}_listen(){this._subscribing+=1;let e=this._listening.then(()=>this._subscribeOnce()).finally(()=>{this._subscribing-=1});return this._listening=e.catch(()=>{}),e}async _subscribeOnce(){let e=this._unsubscribeWs;this._unsubscribeWs=null,await e?.().catch(()=>{});try{let i=await Ut(this.hass.connection,this._store.state.entryId,r=>this._onEvent(r));if(!this.isConnected){i().catch(()=>{});return}this._unsubscribeWs=i,this._store.set({connection:"live"}),this._stopPolling()}catch(i){ae(i)||console.warn("MyHOME panel: live updates are not available",A(i)),this._store.set({connection:"polling"}),this._startPolling()}}_onEvent(e){if(e.type==="overview"){this._store.setOverview(e.overview),this._followPush();return}if(e.type==="measuring"){let i=this._store.state.overview;if(!i)return;this._store.set({overview:{...i,measuring:e.cover_unique_id?{cover_unique_id:e.cover_unique_id,name:e.name??""}:null}}),e.cover_unique_id&&(this._store.set({armed:null,drag:null}),this._store.announce(this._i18n.t("panel.banner.measuring.body",{cover:e.name??""})))}}_followPush(){if(this._followTimer)return;let e=Math.max(0,An-(Date.now()-this._followedAt));this._followTimer=setTimeout(()=>{this._followTimer=null,this._followedAt=Date.now(),this._store.state.review&&this._schedulePreview(),this._store.state.detail.for&&this._loadDetail()},e)}_startPolling(){this._poll||(this._poll=setInterval(()=>{document.hidden||this._refresh()},Tn))}_stopPolling(){this._poll&&(clearInterval(this._poll),this._poll=null)}_onRoute(e){if(this._drawerBack=pi(this._drawerBack,this._store.state.route,e),this._store.set({route:e}),e.view==="cover"){let i=e.params.id;this._store.state.detail.for!==i&&(this._store.set({detail:{...ce,for:i,loading:!0}}),this._loadDetail())}else this._store.state.detail.for!==null&&this._store.set({detail:ce});if(e.view==="profile"){let i=e.params.name;this._store.state.profile.for!==i&&this._store.set({profile:{...he,for:i}})}else this._store.state.profile.for!==null&&this._store.set({profile:he});this._started&&this._store.set({writeError:null})}get _version(){return this.panel?.config?.version??""}_navigate(e){this._router.navigate(e)}_renderMenuButton(){return this.narrow?Jt("ha-menu-button")?a`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:a`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${()=>ei(this)}
    >
      ☰
    </button>`:l}_renderPlaceholder(e,i){let r={id:"panel.common.not_yet",model:"lettura",title:e,body:i,secondary:[{label:this._i18n.t("panel.common.action.back"),action:"back",kind:"text"}]};return a`<myhome-screen
      .model=${r}
      .i18n=${this._i18n}
      @myhome-screen-action=${o=>{o.detail?.action==="back"&&this._navigate("/")}}
    ></myhome-screen>`}get _locked(){let e=this._store.state;return e.overview?.measuring!=null||e.applying}async _confirm(){let e=this._store.state,i=e.entryId;if(this._locked||!i||e.pending.length===0)return;if(e.pending.filter(p=>{let d=e.overview?.covers.find(c=>c.unique_id===p.cover);return d!==void 0&&si(d,p)&&le(e.heights[p.cover])!==null}).length>0){this._store.set({heightsForced:!0}),this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));return}let o=pt(e.pending,e.heights,e.overview?.covers??[]),s=e.order??void 0;this._store.announce(this._i18n.t("panel.assign.announce.applying")),await this._write(()=>Wt(this.hass.connection,i,o,s),p=>{this._store.set({...Ee}),this._store.setOverview(p.overview),this._snack(p.applied===1?this._i18n.t("panel.toast.assigned_one"):this._i18n.t("panel.toast.assigned",{count:p.applied}),p.undo_token)})}async _undo(){let e=this._store.state,i=e.snack?.undoToken;if(!i||!e.entryId)return;let r=e.entryId;this._clearSnack(),await this._write(()=>Zt(this.hass.connection,r,i),o=>{this._store.setOverview(o.overview),this._snack(this._i18n.t("panel.toast.undone"),null)})}async _write(e,i,r){this._store.set({applying:!0,writeError:null});try{let o=await e();this._store.set({applying:!1}),i(o)}catch(o){let s=A(o);this._store.set({applying:!1,writeError:s});let p=this._i18n.refusal(s.translation_key,s.translation_placeholders??{});this._store.announce(p),r?.(p)}}_snack(e,i,r=!0){this._clearSnack(),this._store.set({snack:{message:e,undoToken:i}}),r&&this._store.announce(e),this._snackTimer=setTimeout(()=>{this._snackTimer=null,this._store.set({snack:null})},Cn)}_clearSnack(){this._snackTimer&&(clearTimeout(this._snackTimer),this._snackTimer=null),this._store.set({snack:null})}_schedulePreview(){this._store.state.review&&(this._previewTimer&&clearTimeout(this._previewTimer),this._previewTimer=setTimeout(()=>{this._previewTimer=null,this._refreshPreview()},vt))}async _refreshPreview(){let e=this._store.state;if(!e.entryId||e.pending.length===0){this._store.set({preview:null});return}let i=++this._previewSeq;this._store.set({previewing:!0});try{let r=await be(this.hass.connection,e.entryId,pt(e.pending,e.heights,e.overview?.covers??[]));i===this._previewSeq&&this._store.set({preview:r.items,previewing:!1})}catch(r){i===this._previewSeq&&this._store.set({previewing:!1}),ae(r)||console.warn("MyHOME panel: the preview could not be read",A(r))}}get _detailCover(){let e=this._store.state,i=e.detail.for;return e.overview?.covers.find(r=>r.unique_id===i)??null}async _loadDetail(){let e=this._store.state,i=e.detail.for;if(!(!this._started||!this.hass||!i||!e.entryId))try{let r=await qt(this.hass.connection,e.entryId,i);if(this._store.state.detail.for!==i)return;this._store.set({detail:{...this._store.state.detail,answer:r,loading:!1,error:null}})}catch(r){if(this._store.state.detail.for!==i)return;this._store.set({detail:{...this._store.state.detail,answer:null,loading:!1,error:A(r)}})}}_detailForm(){let e=this._store.state.detail.answer,i={};for(let r of Q){let o=e?.keys.find(s=>s.key===r);i[r]=o&&o.own?this._i18n.number(o.value,L[r]??1):""}return i}async _saveValues(){let e=this._store.state,i=e.detail.for;if(this._locked||!i||!e.entryId)return;let r={};for(let d of Q){let c=e.detail.form[d];if(b(d,c)!==null)return;r[d]=$(c)?null:I(c??"")}let o=Object.values(r).every(d=>d===null),s=this._detailCover?.name??"",p=e.entryId;await this._write(()=>Gt(this.hass.connection,p,i,r),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{}}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(o?this._i18n.t("panel.toast.measure_removed",{cover:s,destination:this._destinationOf(d.overview,i)}):this._i18n.t("panel.toast.values_saved",{cover:s}),d.undo_token)})}async _saveTravel(){let e=this._store.state,i=e.detail.for,r=e.detail.form.height;if(this._locked||!i||!e.entryId||$(r)||b("height",r))return;let o=I(r??""),s=this._detailCover?.name??"",p=e.entryId;await this._write(()=>Kt(this.hass.connection,p,i,o),d=>{this._store.set({detail:{...this._store.state.detail,mode:"view",form:{},preview:null}}),this._store.setOverview(d.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.travel_saved",{cover:s}),d.undo_token)})}async _removeMeasure(){let e=this._store.state,i=e.detail.for;if(this._locked||!i||!e.entryId)return;let r=this._detailCover?.name??"",o=e.entryId;await this._write(()=>jt(this.hass.connection,o,i),s=>{this._store.set({detail:{...this._store.state.detail,mode:"view"}}),this._store.setOverview(s.overview),this._loadDetail(),this._snack(this._i18n.t("panel.toast.measure_removed",{cover:r,destination:s.falls_back_to==="profile"?this._i18n.t("panel.detail.destination.profile",{profile:s.profile??""}):s.falls_back_to==="file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}),s.undo_token)})}_destinationOf(e,i){let r=e.covers.find(o=>o.unique_id===i);return r?.origin==="inherited"||r?.origin==="adjusted"?this._i18n.t("panel.detail.destination.profile",{profile:r.profile??""}):r?.origin==="from_the_file"?this._i18n.t("panel.detail.destination.file"):this._i18n.t("panel.detail.destination.defaults")}_scheduleTravelPreview(){this._travelTimer&&clearTimeout(this._travelTimer),this._travelTimer=setTimeout(()=>{this._travelTimer=null,this._refreshTravelPreview()},vt)}async _refreshTravelPreview(){let e=this._store.state,i=this._detailCover,r=e.detail.form.height;if(!e.entryId||!i||$(r)||b("height",r)!==null){this._store.set({detail:{...this._store.state.detail,preview:null}});return}let o=++this._previewSeq;this._store.set({detail:{...this._store.state.detail,previewing:!0}});try{let s=await be(this.hass.connection,e.entryId,[{...dt(i),height:I(r??"")}]);if(o!==this._previewSeq)return;this._store.set({detail:{...this._store.state.detail,preview:s.items[0]??null,previewing:!1}})}catch(s){o===this._previewSeq&&this._store.set({detail:{...this._store.state.detail,previewing:!1}}),ae(s)||console.warn("MyHOME panel: the preview could not be read",A(s))}}_openFlow(e){li({source:e,entryId:this._store.state.entryId,onLeaving:()=>this._store.announce(this._i18n.t("panel.common.opens_configure"))})}_drawerTitle(){let e=this._store.state,i=e.route;if(i.view==="cover"){let r=this._detailCover;return r?r.name:this._i18n.t("panel.detail.title")}return i.view==="profile"?e.overview?.profiles.some(o=>o.name===i.params.name)?this._i18n.t("panel.profile.name",{profile:i.params.name}):this._i18n.t("panel.profile.title"):this._i18n.t("panel.overview.title")}_title(){return this._i18n.t("panel.overview.title")}get _profileRow(){let e=this._store.state;return e.overview?.profiles.find(i=>i.name===e.profile.for)??null}_followersOf(e){let i=this._store.state.overview?.covers??[];if(!e)return[];let r=new Set([...e.followers,...e.followers_from_file]);return i.filter(o=>r.has(o.unique_id))}_profileForm(e){let i={};for(let r of J){let o=r==="reference_height"?e?.reference_height:e?.values[r];i[r]=o==null?"":this._i18n.number(o,L[r]??0)}return i}_typedProfile(){let e=this._store.state.profile.form,i={};for(let r of J){if($(e[r])||b(r,e[r])!==null)return null;i[r]=I(e[r]??"")}return i}async _saveProfile(){let e=this._store.state,i=e.profile.for,r=this._typedProfile();if(this._locked||!i||!e.entryId||!r)return;let{reference_height:o,...s}=r,p=e.entryId;await this._write(()=>Vt(this.hass.connection,p,i,s,o),d=>{this._store.set({profile:{...this._store.state.profile,mode:"view",impact:null}}),this._store.setOverview(d.overview),this._snack(d.affected.length===1?this._i18n.t("panel.toast.profile_saved_one",{profile:i}):this._i18n.t("panel.toast.profile_saved",{profile:i,count:d.affected.length}),d.undo_token)})}async _renameProfile(){let e=this._store.state,i=e.profile.for,r=e.profile.newName.trim();if(this._locked||!i||!e.entryId||!r||r===i)return;let o=e.entryId;await this._write(()=>Yt(this.hass.connection,o,i,r),s=>{this._store.setOverview(s.overview),this._navigate(`/profile/${encodeURIComponent(r)}`),this._snack(this._i18n.t("panel.toast.profile_renamed",{profile:r}),s.undo_token)},s=>this._store.set({profile:{...this._store.state.profile,nameError:s},writeError:null}))}async _deleteProfile(){let e=this._store.state,i=e.profile.for;if(this._locked||!i||!e.entryId)return;let r=e.entryId;await this._write(()=>Xt(this.hass.connection,r,i),o=>{this._store.setOverview(o.overview),this._navigate("/"),this._snack(this._i18n.t("panel.toast.profile_deleted",{profile:i}),o.undo_token)})}_scheduleImpact(){this._impactTimer&&clearTimeout(this._impactTimer),this._impactTimer=setTimeout(()=>{this._impactTimer=null,this._refreshImpact()},vt)}async _refreshImpact(){let e=this._store.state,i=this._typedProfile(),r=e.profile.for,o=this._followersOf(this._profileRow);if(!e.entryId||!r||!i||o.length===0){this._store.set({profile:{...this._store.state.profile,impact:null}});return}let s=++this._previewSeq;this._store.set({profile:{...this._store.state.profile,impacting:!0}});try{let p=await be(this.hass.connection,e.entryId,o.map(d=>dt(d)),{[r]:i});if(s!==this._previewSeq)return;this._store.set({profile:{...this._store.state.profile,impact:p.items,impacting:!1}})}catch(p){s===this._previewSeq&&this._store.set({profile:{...this._store.state.profile,impacting:!1}}),ae(p)||console.warn("MyHOME panel: the impact preview could not be read",A(p))}}async _retry(){await this._refresh(),this._store.state.connection!=="live"&&await this._listen()}_renderView(){let e=this._store.state;if(e.status==="loading")return xi(this._i18n);if(e.status==="error"||!e.overview){let r=e.error;return a`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(r?.translation_key,r?.translation_placeholders??{})}
        </div>
        <div class="soft">${r?`${r.code}: ${r.message}`:""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${()=>{this._retry()}}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${k}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version?a` · ${this._version}`:l}
        </div>
      </div>`}let i=e.route;return i.view!=="overview"&&!B(i)?this._renderPlaceholder(this._i18n.t("panel.overview.title"),this._i18n.t("panel.common.not_yet")):a`<myhome-overview
      .i18n=${this._i18n}
      .state=${e}
      .actions=${this._assignActions}
    ></myhome-overview>`}_renderDrawer(){let e=this._store.state;if(!B(e.route)||e.status==="error")return l;let i=e.status==="loading"?Me(this._i18n):e.route.view==="cover"?a`<myhome-cover-detail
              .i18n=${this._i18n}
              .state=${e}
              .actions=${this._detailActions}
            ></myhome-cover-detail>`:a`<myhome-profile-card
              .i18n=${this._i18n}
              .state=${e}
              .actions=${this._profileActions}
            ></myhome-profile-card>`;return vi({i18n:this._i18n,title:this._drawerTitle(),hasBack:this._drawerBack!==null,applying:e.applying,onClose:this._closeDrawer,content:i})}render(){let e=this._store.state,i=this._title(),r=e.overview?.measuring??null,o=e.route.view!=="overview";return a`
      <!--
        One named landmark for everything the panel draws, and deliberately not "main" or
        "banner": a custom panel is rendered inside Home Assistant's own document and the
        shell owns those. A region named by the page's own heading is a landmark a reader
        can jump to and one that cannot collide with the host's.
      -->
      <div class="page" role="region" aria-labelledby="panel-title">
        <div class="toolbar">
          ${this._renderMenuButton()}
          <h1 class="title" id="panel-title">${i}</h1>
          ${this._renderGatewayPicker()}
        </div>
      ${e.connection==="offline"?a`<div class="offline" role="status">
            ${this._i18n.t("panel.error.no_connection")}
          </div>`:l}
      ${r?fi(this._i18n,r.name,k):l}
      <div class="content">
        ${mi(e.announce)} ${this._renderView()}
        ${e.connection==="polling"&&e.status==="ready"?a`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`:l}
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
      ${o&&e.applying?Oe(this._i18n):l}
      ${o&&e.snack&&!e.applying?De(this._i18n,e.snack.message,e.snack.undoToken?()=>{this._undo()}:null):l}
      </div>
    `}_renderGatewayPicker(){let e=this._store.state,i=e.overview?.entries??[],r=i.find(s=>s.entry_id===e.entryId);if(i.length<=1)return l;let o=this._i18n.t("panel.common.gateway",{gateway:r?.title??""});return a`<select
      class="gateway"
      aria-label=${o}
      .value=${e.entryId??""}
      ?disabled=${e.applying}
      @change=${s=>{this._switchGateway(s.target.value)}}
    >
      ${i.map(s=>a`<option value=${s.entry_id} ?selected=${s.entry_id===e.entryId}>
          ${s.title}
        </option>`)}
    </select>`}async _switchGateway(e){if(!e||e===this._store.state.entryId)return;let i=this._unsubscribeWs;this._unsubscribeWs=null,await i?.().catch(()=>{}),this._clearSnack(),this._store.set({...Ee,entryId:e,detail:ce,profile:he,search:"",room:"",snack:null}),this._navigate("/"),await this._refresh(),await this._listen()}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",gt);export{gt as MyHomeCalibrationPanel};
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
