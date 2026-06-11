import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useBOM } from '../context/BOMContext';
import { 
  Play, RefreshCw, AlertTriangle, AlertCircle, CheckCircle, 
  Cpu, Zap, Info, Layers, Radio, HardDrive, Download, Loader2
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || '';

interface LogicalBlock {
  id: string;
  type: string;
  description: string;
  voltage_domain: string;
}

interface BlockConnection {
  source_block_id: string;
  target_block_id: string;
  type: string;
  description: string;
}

interface BlockDiagramData {
  blocks: LogicalBlock[];
  connections: BlockConnection[];
}

interface PinSpec {
  number: string;
  name: string;
  type: string;
}

interface ComponentInstance {
  reference: string;
  mpn: string;
  supplier_id: string;
  value: string;
  pins: PinSpec[];
  block_id?: string;
}

interface PinRef {
  component_ref: string;
  pin_number: string;
}

interface NetConnection {
  name: string;
  connections: PinRef[];
}

interface SchematicIRData {
  components: ComponentInstance[];
  nets: NetConnection[];
}

interface ErcViolation {
  severity: 'ERROR' | 'WARNING';
  rule: string;
  message: string;
  elements: string[];
}

interface CompiledFile {
  kind: string;
  filename: string;
  download_url: string;
}

interface CompileResult {
  download_url: string;
  filename: string;
  files?: CompiledFile[];
}

export const Dashboard: React.FC = () => {
  const { projectId } = useBOM();
  const [activeSubTab, setActiveSubTab] = useState<'blocks' | 'netlist'>('blocks');
  
  const [blocksData, setBlocksData] = useState<BlockDiagramData>({ blocks: [], connections: [] });
  const [irData, setIrData] = useState<SchematicIRData>({ components: [], nets: [] });
  const [ercViolations, setErcViolations] = useState<ErcViolation[]>([]);
  
  const [loading, setLoading] = useState(false);
  const [compiling, setCompiling] = useState(false);
  const [compileResult, setCompileResult] = useState<CompileResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const [blocksRes, irRes, ercRes] = await Promise.all([
        axios.get<BlockDiagramData>(`${API_BASE}/api/projects/${projectId}/block-diagram`),
        axios.get<SchematicIRData>(`${API_BASE}/api/projects/${projectId}/schematic-ir`),
        axios.get<ErcViolation[]>(`${API_BASE}/api/projects/${projectId}/erc`)
      ]);
      setBlocksData(blocksRes.data);
      setIrData(irRes.data);
      setErcViolations(ercRes.data);
    } catch (err: any) {
      console.error('Failed to load dashboard data', err);
      setError('Could not fetch project dashboard state from server.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCompile = async () => {
    if (!projectId) return;
    setCompiling(true);
    setError(null);
    setCompileResult(null);
    try {
      const res = await axios.post(`${API_BASE}/api/projects/${projectId}/schematic-ir/compile`);
      setCompileResult(res.data);
    } catch (err: any) {
      console.error('Compilation failed', err);
      setError(err.response?.data?.detail || 'Failed to compile Schematic IR to KiCad 9 format.');
    } finally {
      setCompiling(false);
    }
  };

  const getSeverityIcon = (sev: string) => {
    if (sev === 'ERROR') return <AlertTriangle className="h-5 w-5 text-red-500" />;
    return <AlertCircle className="h-5 w-5 text-yellow-500" />;
  };

  const getSeverityColorClass = (sev: string) => {
    if (sev === 'ERROR') return 'border-red-200 bg-red-50 text-red-900';
    return 'border-yellow-200 bg-yellow-50 text-yellow-900';
  };

  const getBlockIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('mcu') || t.includes('micro')) return <Cpu className="h-5 w-5 text-blue-600" />;
    if (t.includes('regulator') || t.includes('power') || t.includes('ldo')) return <Zap className="h-5 w-5 text-orange-600" />;
    if (t.includes('sensor')) return <Radio className="h-5 w-5 text-indigo-600" />;
    if (t.includes('connector') || t.includes('port')) return <HardDrive className="h-5 w-5 text-emerald-600" />;
    return <Info className="h-5 w-5 text-gray-600" />;
  };

  if (!projectId) {
    return <div className="text-center py-10 text-gray-500">Connecting to project database...</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto bg-white rounded-lg shadow border border-gray-200 text-gray-800">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 pb-4 border-b">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Project Design Board</h2>
          <p className="text-sm text-gray-500">Decompose specs, manage connections, and verify schematic integrity in real-time.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 border rounded hover:bg-gray-100 flex items-center justify-center disabled:opacity-50"
            title="Refresh state"
          >
            <RefreshCw className={`h-5 w-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleCompile}
            disabled={compiling || irData.components.length === 0}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 font-medium"
          >
            {compiling ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Compiling...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" /> Compile to KiCad 9
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-md border border-red-200 bg-red-50 text-red-800 text-sm">
          {error}
        </div>
      )}

      {compileResult && (
        <div className="mb-6 p-4 rounded-md border border-green-200 bg-green-50 text-green-900">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <span className="font-bold">Success!</span> Compiled KiCad project <code className="font-mono text-sm bg-green-100 px-1 py-0.5 rounded">{compileResult.filename}</code>.
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {(compileResult.files && compileResult.files.length > 0
                ? compileResult.files
                : [{ kind: 'schematic', filename: compileResult.filename, download_url: compileResult.download_url }]
              ).map((file) => (
                <a
                  key={file.download_url}
                  href={`${API_BASE}${file.download_url}`}
                  className="bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700 flex items-center gap-2 text-sm font-semibold capitalize"
                  title={file.filename}
                >
                  <Download className="h-4 w-4" /> {file.kind.replace(/_/g, ' ')}
                </a>
              ))}
            </div>
          </div>
          <p className="text-xs text-green-700 mt-2">
            Open the project in KiCad 9 and run "Update PCB from Schematic" to start board layout — footprints are pre-assigned where the package was recognized.
          </p>
        </div>
      )}

      {loading && blocksData.blocks.length === 0 && irData.components.length === 0 ? (
        <div className="text-center py-20 text-gray-500">Loading design status...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left panel (Blocks or Netlist IR) */}
          <div className="lg:col-span-2 flex flex-col border rounded-lg bg-gray-50 overflow-hidden min-h-[500px]">
            {/* Sub-tab selection */}
            <div className="flex border-b bg-white">
              <button
                onClick={() => setActiveSubTab('blocks')}
                className={`flex-1 py-3 text-center border-b-2 font-semibold text-sm ${
                  activeSubTab === 'blocks'
                    ? 'border-blue-600 text-blue-600 bg-blue-50/30'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                1. Logical Architecture (Blocks)
              </button>
              <button
                onClick={() => setActiveSubTab('netlist')}
                className={`flex-1 py-3 text-center border-b-2 font-semibold text-sm ${
                  activeSubTab === 'netlist'
                    ? 'border-blue-600 text-blue-600 bg-blue-50/30'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                2. Structural Netlist (Schematic IR)
              </button>
            </div>

            <div className="p-6 flex-1 overflow-y-auto max-h-[550px]">
              {/* TAB 1: Logical Block Diagram */}
              {activeSubTab === 'blocks' && (
                <div className="space-y-6">
                  {blocksData.blocks.length === 0 ? (
                    <div className="text-center py-16 text-gray-500 flex flex-col items-center justify-center">
                      <Layers className="h-12 w-12 text-gray-400 mb-3" />
                      <p className="font-semibold">No logical blocks created yet.</p>
                      <p className="text-sm max-w-sm mt-1">Ask the assistant to decompose your design requirements into a block diagram to get started.</p>
                    </div>
                  ) : (
                    <>
                      <div>
                        <h3 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wider">Logical Modules</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {blocksData.blocks.map((block) => (
                            <div key={block.id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex gap-3 hover:shadow-md transition-shadow">
                              <div className="mt-1 flex-shrink-0 bg-blue-50 p-2 rounded-lg h-fit">
                                {getBlockIcon(block.type)}
                              </div>
                              <div className="flex-1">
                                <div className="flex justify-between items-start">
                                  <span className="font-bold text-gray-900">{block.id}</span>
                                  <span className="text-xs bg-gray-100 px-2 py-0.5 rounded font-medium text-gray-600 uppercase">
                                    {block.voltage_domain}
                                  </span>
                                </div>
                                <div className="text-xs text-blue-600 font-semibold">{block.type}</div>
                                <p className="text-xs text-gray-500 mt-2">{block.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {blocksData.connections.length > 0 && (
                        <div>
                          <h3 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wider">Bus & Rail Interconnects</h3>
                          <div className="space-y-2">
                            {blocksData.connections.map((conn, idx) => (
                              <div key={idx} className="bg-white p-3 rounded-lg shadow-sm border border-gray-200 flex items-center justify-between text-sm">
                                <div className="flex items-center gap-3">
                                  <span className="font-semibold text-gray-700">{conn.source_block_id}</span>
                                  <span className="text-gray-400">➔</span>
                                  <span className="font-semibold text-gray-700">{conn.target_block_id}</span>
                                </div>
                                <div className="text-right">
                                  <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded font-semibold">{conn.type}</span>
                                  {conn.description && (
                                    <div className="text-xs text-gray-500 mt-0.5">{conn.description}</div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* TAB 2: Structural Netlist IR */}
              {activeSubTab === 'netlist' && (
                <div className="space-y-6">
                  {irData.components.length === 0 ? (
                    <div className="text-center py-16 text-gray-500 flex flex-col items-center justify-center">
                      <HardDrive className="h-12 w-12 text-gray-400 mb-3" />
                      <p className="font-semibold">No components placed in schematic IR yet.</p>
                      <p className="text-sm max-w-sm mt-1">Once parts are mapped to logical blocks, the assistant will populate the Netlist IR and wire them up.</p>
                    </div>
                  ) : (
                    <>
                      <div>
                        <h3 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wider">Placed Components</h3>
                        <div className="space-y-3">
                          {irData.components.map((comp) => (
                            <div key={comp.reference} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
                              <div className="flex justify-between items-start mb-2">
                                <div>
                                  <span className="font-bold text-lg text-blue-700 mr-2">{comp.reference}</span>
                                  <span className="font-mono text-sm text-gray-600 bg-gray-50 px-1.5 py-0.5 rounded">{comp.mpn}</span>
                                </div>
                                {comp.block_id && (
                                  <span className="text-xs border border-blue-200 text-blue-600 px-2 py-0.5 rounded bg-blue-50/55 font-medium">
                                    logical: {comp.block_id}
                                  </span>
                                )}
                              </div>
                              <div className="grid grid-cols-2 gap-4 text-xs mt-2 border-t pt-2 text-gray-500">
                                <div><span className="font-medium text-gray-700">LCSC Part:</span> {comp.supplier_id}</div>
                                <div><span className="font-medium text-gray-700">Value:</span> {comp.value || 'N/A'}</div>
                              </div>
                              <div className="mt-3">
                                <div className="text-xs font-semibold text-gray-700 mb-1">Pinout Details ({comp.pins.length} pins):</div>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                  {comp.pins.map((pin) => (
                                    <div key={pin.number} className="bg-gray-50 p-1.5 rounded flex items-center justify-between text-xs">
                                      <span className="font-bold text-gray-600 bg-gray-200 px-1 rounded font-mono mr-1">{pin.number}</span>
                                      <span className="flex-1 truncate font-medium ml-1" title={pin.name}>{pin.name}</span>
                                      <span className={`text-[10px] px-1 rounded capitalize font-medium ${
                                        pin.type.includes('power') ? 'bg-orange-100 text-orange-800' :
                                        pin.type.includes('input') ? 'bg-blue-100 text-blue-800' :
                                        pin.type.includes('output') ? 'bg-green-100 text-green-800' :
                                        'bg-gray-200 text-gray-800'
                                      }`}>
                                        {pin.type.replace('_', ' ')}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {irData.nets.length > 0 && (
                        <div>
                          <h3 className="font-bold text-gray-700 mb-3 text-sm uppercase tracking-wider">Electrical Connections (Nets)</h3>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {irData.nets.map((net) => (
                              <div key={net.name} className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
                                <div className="font-bold text-gray-900 border-b pb-1 mb-2 flex justify-between items-center text-xs">
                                  <span>NET: {net.name}</span>
                                  <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono text-[10px]">
                                    {net.connections.length} nodes
                                  </span>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {net.connections.map((conn, cIdx) => (
                                    <span key={cIdx} className="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded text-[11px] font-mono border">
                                      {conn.component_ref}.{conn.pin_number}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right panel (ERC Violations) */}
          <div className="flex flex-col border rounded-lg bg-gray-50 overflow-hidden min-h-[500px]">
            <div className="bg-white p-4 border-b flex justify-between items-center">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-gray-500" /> Electrical Check (ERC)
              </h3>
              {ercViolations.length > 0 && (
                <span className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded-full font-bold">
                  {ercViolations.length} issues
                </span>
              )}
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto space-y-3 max-h-[550px]">
              {ercViolations.length === 0 ? (
                <div className="text-center py-20 text-green-700 bg-white rounded-lg shadow-sm border border-green-150 p-6 flex flex-col items-center justify-center">
                  <CheckCircle className="h-12 w-12 text-green-500 mb-3" />
                  <p className="font-bold text-base">All ERC Checks Passed!</p>
                  <p className="text-xs text-green-600 mt-2 max-w-[200px]">No floating inputs, short circuits, or missing decoupling caps detected.</p>
                </div>
              ) : (
                ercViolations.map((viol, index) => (
                  <div key={index} className={`p-4 rounded-lg border-l-4 shadow-sm bg-white ${getSeverityColorClass(viol.severity)}`}>
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex-shrink-0">
                        {getSeverityIcon(viol.severity)}
                      </div>
                      <div className="flex-1">
                        <div className="font-bold text-xs uppercase tracking-wide flex justify-between">
                          <span>{viol.rule}</span>
                          <span className={viol.severity === 'ERROR' ? 'text-red-600' : 'text-yellow-600'}>
                            {viol.severity}
                          </span>
                        </div>
                        <p className="text-sm mt-1 text-gray-700 font-medium leading-relaxed">{viol.message}</p>
                        {viol.elements.length > 0 && (
                          <div className="mt-2.5 flex flex-wrap gap-1 items-center">
                            <span className="text-[10px] text-gray-500 mr-1 uppercase font-semibold">Targets:</span>
                            {viol.elements.map((el, elIdx) => (
                              <span key={elIdx} className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-[10px] font-mono border">
                                {el}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
