import express from 'express';
const app = express(); const api = process.env.ANALYTICS_API || 'http://127.0.0.1:8000'; const port = Number(process.env.PORT || 3001);
app.use(express.json());
app.use('/api', async (req,res) => { try { const response=await fetch(`${api}${req.originalUrl}`,{method:req.method,headers:{'content-type':'application/json'},body:['GET','HEAD'].includes(req.method)?undefined:JSON.stringify(req.body)}); const body=await response.text(); const disposition=response.headers.get('content-disposition'); if(disposition)res.setHeader('Content-Disposition',disposition); res.status(response.status).type(response.headers.get('content-type')||'application/json').send(body); } catch { res.status(502).json({detail:'Analytics service is unavailable'}); } });
app.listen(port,()=>console.log(`Node gateway listening on http://127.0.0.1:${port}`));
