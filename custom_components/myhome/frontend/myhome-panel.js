/* MyHOME calibration panel */
var M=globalThis,N=M.ShadowRoot&&(M.ShadyCSS===void 0||M.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,z=Symbol(),ee=new WeakMap,S=class{constructor(e,t,s){if(this._$cssResult$=!0,s!==z)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(N&&e===void 0){let s=t!==void 0&&t.length===1;s&&(e=ee.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),s&&ee.set(t,e))}return e}toString(){return this.cssText}},te=i=>new S(typeof i=="string"?i:i+"",void 0,z),C=(i,...e)=>{let t=i.length===1?i[0]:e.reduce((s,r,o)=>s+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(r)+i[o+1],i[0]);return new S(t,i,z)},se=(i,e)=>{if(N)i.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let s=document.createElement("style"),r=M.litNonce;r!==void 0&&s.setAttribute("nonce",r),s.textContent=t.cssText,i.appendChild(s)}},D=N?i=>i:i=>i instanceof CSSStyleSheet?(e=>{let t="";for(let s of e.cssRules)t+=s.cssText;return te(t)})(i):i;var{is:we,defineProperty:Ee,getOwnPropertyDescriptor:Se,getOwnPropertyNames:Ce,getOwnPropertySymbols:Pe,getPrototypeOf:Te}=Object,L=globalThis,re=L.trustedTypes,Re=re?re.emptyScript:"",He=L.reactiveElementPolyfillSupport,P=(i,e)=>i,W={toAttribute(i,e){switch(e){case Boolean:i=i?Re:null;break;case Object:case Array:i=i==null?i:JSON.stringify(i)}return i},fromAttribute(i,e){let t=i;switch(e){case Boolean:t=i!==null;break;case Number:t=i===null?null:Number(i);break;case Object:case Array:try{t=JSON.parse(i)}catch{t=null}}return t}},oe=(i,e)=>!we(i,e),ie={attribute:!0,type:String,converter:W,reflect:!1,useDefault:!1,hasChanged:oe};Symbol.metadata??=Symbol("metadata"),L.litPropertyMetadata??=new WeakMap;var m=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=ie){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let s=Symbol(),r=this.getPropertyDescriptor(e,s,t);r!==void 0&&Ee(this.prototype,e,r)}}static getPropertyDescriptor(e,t,s){let{get:r,set:o}=Se(this.prototype,e)??{get(){return this[t]},set(n){this[t]=n}};return{get:r,set(n){let c=r?.call(this);o?.call(this,n),this.requestUpdate(e,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??ie}static _$Ei(){if(this.hasOwnProperty(P("elementProperties")))return;let e=Te(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(P("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(P("properties"))){let t=this.properties,s=[...Ce(t),...Pe(t)];for(let r of s)this.createProperty(r,t[r])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[s,r]of t)this.elementProperties.set(s,r)}this._$Eh=new Map;for(let[t,s]of this.elementProperties){let r=this._$Eu(t,s);r!==void 0&&this._$Eh.set(r,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let s=new Set(e.flat(1/0).reverse());for(let r of s)t.unshift(D(r))}else e!==void 0&&t.push(D(e));return t}static _$Eu(e,t){let s=t.attribute;return s===!1?void 0:typeof s=="string"?s:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return se(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){let s=this.constructor.elementProperties.get(e),r=this.constructor._$Eu(e,s);if(r!==void 0&&s.reflect===!0){let o=(s.converter?.toAttribute!==void 0?s.converter:W).toAttribute(t,s.type);this._$Em=e,o==null?this.removeAttribute(r):this.setAttribute(r,o),this._$Em=null}}_$AK(e,t){let s=this.constructor,r=s._$Eh.get(e);if(r!==void 0&&this._$Em!==r){let o=s.getPropertyOptions(r),n=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:W;this._$Em=r;let c=n.fromAttribute(t,o.type);this[r]=c??this._$Ej?.get(r)??c,this._$Em=null}}requestUpdate(e,t,s,r=!1,o){if(e!==void 0){let n=this.constructor;if(r===!1&&(o=this[e]),s??=n.getPropertyOptions(e),!((s.hasChanged??oe)(o,t)||s.useDefault&&s.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(n._$Eu(e,s))))return;this.C(e,t,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:r,wrapped:o},n){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,n??t??this[e]),o!==!0||n!==void 0)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),r===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[r,o]of this._$Ep)this[r]=o;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[r,o]of s){let{wrapped:n}=o,c=this[r];n!==!0||this._$AL.has(r)||c===void 0||this.C(r,void 0,o,c)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(t)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};m.elementStyles=[],m.shadowRootOptions={mode:"open"},m[P("elementProperties")]=new Map,m[P("finalized")]=new Map,He?.({ReactiveElement:m}),(L.reactiveElementVersions??=[]).push("2.1.2");var Z=globalThis,ne=i=>i,B=Z.trustedTypes,ae=B?B.createPolicy("lit-html",{createHTML:i=>i}):void 0,ue="$lit$",_=`lit$${Math.random().toFixed(9).slice(2)}$`,me="?"+_,Oe=`<${me}>`,b=document,R=()=>b.createComment(""),H=i=>i===null||typeof i!="object"&&typeof i!="function",G=Array.isArray,Ue=i=>G(i)||typeof i?.[Symbol.iterator]=="function",I=`[ 	
\f\r]`,T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,he=/-->/g,le=/>/g,$=RegExp(`>|${I}(?:([^\\s"'>=/]+)(${I}*=${I}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ce=/'/g,de=/"/g,fe=/^(?:script|style|textarea|title)$/i,Q=i=>(e,...t)=>({_$litType$:i,strings:e,values:t}),f=Q(1),De=Q(2),We=Q(3),A=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),pe=new WeakMap,y=b.createTreeWalker(b,129);function ge(i,e){if(!G(i)||!i.hasOwnProperty("raw"))throw Error("invalid template strings array");return ae!==void 0?ae.createHTML(e):e}var ke=(i,e)=>{let t=i.length-1,s=[],r,o=e===2?"<svg>":e===3?"<math>":"",n=T;for(let c=0;c<t;c++){let a=i[c],d,p,h=-1,u=0;for(;u<a.length&&(n.lastIndex=u,p=n.exec(a),p!==null);)u=n.lastIndex,n===T?p[1]==="!--"?n=he:p[1]!==void 0?n=le:p[2]!==void 0?(fe.test(p[2])&&(r=RegExp("</"+p[2],"g")),n=$):p[3]!==void 0&&(n=$):n===$?p[0]===">"?(n=r??T,h=-1):p[1]===void 0?h=-2:(h=n.lastIndex-p[2].length,d=p[1],n=p[3]===void 0?$:p[3]==='"'?de:ce):n===de||n===ce?n=$:n===he||n===le?n=T:(n=$,r=void 0);let g=n===$&&i[c+1].startsWith("/>")?" ":"";o+=n===T?a+Oe:h>=0?(s.push(d),a.slice(0,h)+ue+a.slice(h)+_+g):a+_+(h===-2?c:g)}return[ge(i,o+(i[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),s]},O=class i{constructor({strings:e,_$litType$:t},s){let r;this.parts=[];let o=0,n=0,c=e.length-1,a=this.parts,[d,p]=ke(e,t);if(this.el=i.createElement(d,s),y.currentNode=this.el.content,t===2||t===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(r=y.nextNode())!==null&&a.length<c;){if(r.nodeType===1){if(r.hasAttributes())for(let h of r.getAttributeNames())if(h.endsWith(ue)){let u=p[n++],g=r.getAttribute(h).split(_),k=/([.?@])?(.*)/.exec(u);a.push({type:1,index:o,name:k[2],strings:g,ctor:k[1]==="."?q:k[1]==="?"?K:k[1]==="@"?F:w}),r.removeAttribute(h)}else h.startsWith(_)&&(a.push({type:6,index:o}),r.removeAttribute(h));if(fe.test(r.tagName)){let h=r.textContent.split(_),u=h.length-1;if(u>0){r.textContent=B?B.emptyScript:"";for(let g=0;g<u;g++)r.append(h[g],R()),y.nextNode(),a.push({type:2,index:++o});r.append(h[u],R())}}}else if(r.nodeType===8)if(r.data===me)a.push({type:2,index:o});else{let h=-1;for(;(h=r.data.indexOf(_,h+1))!==-1;)a.push({type:7,index:o}),h+=_.length-1}o++}}static createElement(e,t){let s=b.createElement("template");return s.innerHTML=e,s}};function x(i,e,t=i,s){if(e===A)return e;let r=s!==void 0?t._$Co?.[s]:t._$Cl,o=H(e)?void 0:e._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),o===void 0?r=void 0:(r=new o(i),r._$AT(i,t,s)),s!==void 0?(t._$Co??=[])[s]=r:t._$Cl=r),r!==void 0&&(e=x(i,r._$AS(i,e.values),r,s)),e}var V=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:s}=this._$AD,r=(e?.creationScope??b).importNode(t,!0);y.currentNode=r;let o=y.nextNode(),n=0,c=0,a=s[0];for(;a!==void 0;){if(n===a.index){let d;a.type===2?d=new U(o,o.nextSibling,this,e):a.type===1?d=new a.ctor(o,a.name,a.strings,this,e):a.type===6&&(d=new J(o,this,e)),this._$AV.push(d),a=s[++c]}n!==a?.index&&(o=y.nextNode(),n++)}return y.currentNode=b,r}p(e){let t=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}},U=class i{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,r){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=r,this._$Cv=r?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=x(this,e,t),H(e)?e===l||e==null||e===""?(this._$AH!==l&&this._$AR(),this._$AH=l):e!==this._$AH&&e!==A&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Ue(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==l&&H(this._$AH)?this._$AA.nextSibling.data=e:this.T(b.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:s}=e,r=typeof s=="number"?this._$AC(e):(s.el===void 0&&(s.el=O.createElement(ge(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===r)this._$AH.p(t);else{let o=new V(r,this),n=o.u(this.options);o.p(t),this.T(n),this._$AH=o}}_$AC(e){let t=pe.get(e.strings);return t===void 0&&pe.set(e.strings,t=new O(e)),t}k(e){G(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,s,r=0;for(let o of e)r===t.length?t.push(s=new i(this.O(R()),this.O(R()),this,this.options)):s=t[r],s._$AI(o),r++;r<t.length&&(this._$AR(s&&s._$AB.nextSibling,r),t.length=r)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let s=ne(e).nextSibling;ne(e).remove(),e=s}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},w=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,r,o){this.type=1,this._$AH=l,this._$AN=void 0,this.element=e,this.name=t,this._$AM=r,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=l}_$AI(e,t=this,s,r){let o=this.strings,n=!1;if(o===void 0)e=x(this,e,t,0),n=!H(e)||e!==this._$AH&&e!==A,n&&(this._$AH=e);else{let c=e,a,d;for(e=o[0],a=0;a<o.length-1;a++)d=x(this,c[s+a],t,a),d===A&&(d=this._$AH[a]),n||=!H(d)||d!==this._$AH[a],d===l?e=l:e!==l&&(e+=(d??"")+o[a+1]),this._$AH[a]=d}n&&!r&&this.j(e)}j(e){e===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},q=class extends w{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===l?void 0:e}},K=class extends w{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==l)}},F=class extends w{constructor(e,t,s,r,o){super(e,t,s,r,o),this.type=5}_$AI(e,t=this){if((e=x(this,e,t,0)??l)===A)return;let s=this._$AH,r=e===l&&s!==l||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,o=e!==l&&(s===l||r);r&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},J=class{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){x(this,e)}};var Me=Z.litHtmlPolyfillSupport;Me?.(O,U),(Z.litHtmlVersions??=[]).push("3.3.3");var _e=(i,e,t)=>{let s=t?.renderBefore??e,r=s._$litPart$;if(r===void 0){let o=t?.renderBefore??null;s._$litPart$=r=new U(e.insertBefore(R(),o),o,void 0,t??{})}return r._$AI(i),r};var X=globalThis,v=class extends m{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=_e(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return A}};v._$litElement$=!0,v.finalized=!0,X.litElementHydrateSupport?.({LitElement:v});var Ne=X.litElementPolyfillSupport;Ne?.({LitElement:v});(X.litElementVersions??=[]).push("4.2.2");var ve=i=>i&&typeof i=="object"&&"code"in i?i:{code:"unknown_error",message:String(i)},$e=(i,e)=>i.sendMessagePromise({type:"myhome/calibration/overview",...e?{entry_id:e}:{}}),ye=(i,e)=>i.sendMessagePromise({type:"myhome/calibration/texts",language:e});var j=class{constructor(){this._texts={};this.language="en"}async load(e,t){let s=await ye(e,t);this._texts=s.texts??{},this.language=s.language}t(e,t){let s=this._texts;for(let r of e.split(".")){if(s===null||typeof s!="object")return t??e;s=s[r]}return typeof s=="string"?s:t??e}};var be=i=>typeof customElements<"u"&&customElements.get(i)!==void 0;var Ae=i=>{i.dispatchEvent(new CustomEvent("hass-toggle-menu",{bubbles:!0,composed:!0}))};var xe=C`
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
    --myhome-divider: var(--divider-color, #e0e0e0);
    --myhome-error: var(--error-color, #db4437);
    --myhome-warning: var(--warning-color, #ffa600);
    --myhome-success: var(--success-color, #43a047);
    --myhome-info: var(--info-color, #039be5);
    --myhome-header: var(--app-header-background-color, var(--primary-color, #03a9f4));
    --myhome-header-text: var(--app-header-text-color, #ffffff);
    --myhome-radius: var(--ha-card-border-radius, 12px);

    display: block;
    min-height: 100%;
    /* The font comes from the host document; the panel never loads one. */
    color: var(--myhome-text);
    background: var(--myhome-background);
  }
`;var E={title:"Profiles and shutters",menu:"Open the sidebar",loading:"Loading…",summary:"{profiles} profiles, {covers} shutters",problem:"The panel could not read this gateway.",configure:"Open Configure instead"},Y=class extends v{constructor(){super();this._i18n=new j;this._overview=null;this._error=null;this._ready=!1;this._language="";this._started=!1;this.narrow=!1,this.panel=null}static{this.properties={hass:{attribute:!1},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1},_overview:{state:!0},_error:{state:!0},_ready:{state:!0}}}static{this.styles=[xe,C`
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        height: 56px;
        padding: 0 8px;
        box-sizing: border-box;
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

      /* The fallback for ha-menu-button: 48x48, like every target in the handoff. */
      button.menu {
        width: 48px;
        height: 48px;
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

      .card {
        background: var(--myhome-card);
        border-radius: var(--myhome-radius);
        box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.12));
        padding: 16px;
        font-size: 14px;
      }

      .card.problem {
        background: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));
        color: var(--myhome-text);
      }

      .soft {
        color: var(--myhome-text-soft);
        font-size: 13px;
        margin-top: 8px;
      }

      a {
        color: var(--myhome-primary);
      }
    `]}shouldUpdate(t){return t.size>1||!t.has("hass")?!0:this._languageOf(this.hass)!==this._language}firstUpdated(){this._bootstrap()}updated(t){if(!(!t.has("hass")||!this.hass)){if(!this._started){this._bootstrap();return}this._ready&&this._languageOf(this.hass)!==this._language&&this._loadTexts()}}_languageOf(t){return t?.locale?.language||t?.language||"en"}async _bootstrap(){if(!(this._started||!this.hass)){this._started=!0,await this._loadTexts();try{this._overview=await $e(this.hass.connection),this._error=null}catch(t){this._error=ve(t)}this._ready=!0}}async _loadTexts(){let t=this._languageOf(this.hass);try{await this._i18n.load(this.hass.connection,t)}catch{}this._language=t,this.requestUpdate()}get _version(){return this.panel?.config?.version??""}_renderMenuButton(){return this.narrow?be("ha-menu-button")?f`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`:f`<button
      class="menu"
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu",E.menu)}
      @click=${()=>Ae(this)}
    >
      ☰
    </button>`:l}_renderBody(){if(!this._ready)return f`<div class="card">${this._i18n.t("panel.common.loading",E.loading)}</div>`;if(this._error||!this._overview){let s=this._error;return f`<div class="card problem">
        <div>${this._i18n.t("panel.error.not_found",E.problem)}</div>
        <div class="soft">${s?`${s.code}: ${s.message}`:""}</div>
        <div class="soft">
          <a href="/config/integrations/integration/myhome"
            >${this._i18n.t("panel.common.action.configure",E.configure)}</a
          >
          ${this._version?f` · ${this._version}`:l}
        </div>
      </div>`}let t=this._i18n.t("panel.overview.summary",E.summary).replace("{profiles}",String(this._overview.profiles.length)).replace("{covers}",String(this._overview.covers.length));return f`<div class="card">
      <div>${t}</div>
      <div class="soft">
        ${this._overview.entries.map(s=>s.title).join(" · ")}
        ${this._version?f` · ${this._version}`:l}
      </div>
    </div>`}render(){let t=this._i18n.t("panel.overview.title",this.panel?.title??E.title);return f`
      <div class="toolbar">
        ${this._renderMenuButton()}
        <div class="title">${t}</div>
      </div>
      <div class="content">${this._renderBody()}</div>
    `}};customElements.get("myhome-calibration-panel")||customElements.define("myhome-calibration-panel",Y);export{Y as MyHomeCalibrationPanel};
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
